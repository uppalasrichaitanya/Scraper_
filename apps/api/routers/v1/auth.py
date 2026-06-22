"""
auth.py — Authentication router.

Endpoints:
  POST /v1/auth/register  — create user, return access token, set refresh cookie
  POST /v1/auth/login     — verify credentials, return access token, set refresh cookie
  POST /v1/auth/refresh   — rotate refresh token, return new access + set new refresh cookie
  POST /v1/auth/logout    — clear refresh cookie
"""

from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from middleware.rate_limiter import limiter
from models.user import ConsentRecord, User, UserProfile
from schemas.token import Token
from schemas.user import UserCreate, UserResponse

logger = structlog.get_logger(__name__)
router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]

_REFRESH_COOKIE = "refresh_token"
_COOKIE_OPTS: dict = dict(
    httponly=True,
    secure=True,        # HTTPS only in prod; overridden in dev via middleware
    samesite="strict",
    path="/v1/auth",    # scoped — not sent on every request
)


def _set_refresh_cookie(response: Response, token: str, max_age_seconds: int) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        max_age=max_age_seconds,
        **_COOKIE_OPTS,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=_REFRESH_COOKIE, path="/v1/auth")


# ── Register ──────────────────────────────────────────────────────────────────
@router.post(
    "/register",
    response_model=Token,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
@limiter.limit("10/15minutes")
async def register(
    request: Request,
    response: Response,
    payload: UserCreate,
    db: DbSession,
) -> Token:
    # Check for duplicate email
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    await db.flush()  # get user.id before creating related records

    # Profile
    profile = UserProfile(
        user_id=user.id,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    db.add(profile)

    # DPDP / consent record
    consent = ConsentRecord(
        user_id=user.id,
        terms_accepted=True,
        privacy_accepted=True,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    db.add(consent)
    await db.commit()

    access_token = create_access_token(str(user.id), role="user")
    refresh_token = create_refresh_token(str(user.id))

    refresh_max_age = 60 * 60 * 24 * 7  # 7 days in seconds
    _set_refresh_cookie(response, refresh_token, refresh_max_age)

    logger.info("user_registered", user_id=str(user.id))
    return Token(access_token=access_token, token_type="bearer", refresh_token=refresh_token)


# ── Login ─────────────────────────────────────────────────────────────────────
@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate and receive tokens",
)
@limiter.limit("10/15minutes")
async def login(
    request: Request,
    response: Response,
    payload: UserCreate,
    db: DbSession,
) -> Token:
    result = await db.execute(select(User).where(User.email == payload.email))
    user: User | None = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    access_token = create_access_token(str(user.id), role="user")
    refresh_token = create_refresh_token(str(user.id))

    _set_refresh_cookie(response, refresh_token, 60 * 60 * 24 * 7)

    logger.info("user_login", user_id=str(user.id))
    return Token(access_token=access_token, token_type="bearer", refresh_token=refresh_token)


# ── Refresh ───────────────────────────────────────────────────────────────────
@router.post(
    "/refresh",
    response_model=Token,
    summary="Rotate refresh token and get new access token",
)
async def refresh(
    response: Response,
    refresh_token: Annotated[str | None, Cookie(alias=_REFRESH_COOKIE)] = None,
) -> Token:
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing.",
        )

    try:
        payload = decode_refresh_token(refresh_token)
    except JWTError:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    user_id: str = payload["sub"]
    new_access = create_access_token(user_id, role="user")
    # Always rotate — old refresh token is implicitly invalidated (stateless rotation)
    new_refresh = create_refresh_token(user_id)

    _set_refresh_cookie(response, new_refresh, 60 * 60 * 24 * 7)

    return Token(access_token=new_access, token_type="bearer", refresh_token=new_refresh)


# ── Logout ────────────────────────────────────────────────────────────────────
@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear refresh token cookie",
)
async def logout(response: Response) -> None:
    _clear_refresh_cookie(response)
