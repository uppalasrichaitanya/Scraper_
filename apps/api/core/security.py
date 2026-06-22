"""
JWT token handling and password hashing.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from jose import JWTError, jwt
import bcrypt

from core.config import settings

logger = structlog.get_logger(__name__)

# ── Password hashing ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


# ── JWT tokens ────────────────────────────────────────────────────────────────
def create_access_token(
    user_id: str,
    role: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a short-lived JWT access token.
    Payload: {sub, role, jti, iat, exp}
    """
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": user_id,
        "role": role,
        "jti": str(uuid.uuid4()),  # unique token ID (allows revocation)
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """
    Create a long-lived refresh token.
    Stored as httpOnly cookie on the client — never in localStorage.
    """
    now = datetime.now(UTC)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": user_id,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": expire,
        "type": "refresh",
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.
    Raises JWTError if invalid, expired, or malformed.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning("JWT decode failed", error=str(e))
        raise


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode access token and verify type == 'access'."""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise JWTError("Expected access token, got refresh token")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode refresh token and verify type == 'refresh'."""
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise JWTError("Expected refresh token, got access token")
    return payload
