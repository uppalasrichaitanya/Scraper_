"""
core/deps.py
Shared FastAPI dependencies — auth, DB session, ES client.

Extract get_current_user here so saved_jobs, alerts, and any future
authenticated routers can import from one place instead of from auth.py.
"""

from __future__ import annotations

from typing import AsyncGenerator
from uuid import UUID

from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import AsyncSessionLocal
from models.user import User


# ------------------------------------------------------------------ #
#  Database session                                                    #
# ------------------------------------------------------------------ #

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session, closing it after the request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ------------------------------------------------------------------ #
#  Current user from JWT                                               #
# ------------------------------------------------------------------ #

async def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Decode the httpOnly access_token cookie and return the authenticated User.
    Raises 401 if the token is missing, expired, or the user no longer exists.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not access_token:
        raise credentials_exc

    try:
        payload = jwt.decode(
            access_token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exc
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except JWTError:
        raise credentials_exc

    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exc

    return user


# ------------------------------------------------------------------ #
#  Optional current user (for public endpoints that benefit from auth) #
# ------------------------------------------------------------------ #

async def get_optional_user(
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Like get_current_user but returns None instead of raising 401."""
    if not access_token:
        return None
    try:
        return await get_current_user(access_token=access_token, db=db)
    except HTTPException:
        return None
