"""
test_security.py — Unit tests for JWT encode/decode and password hashing.
No database required.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from jose import JWTError, jwt

from core.config import settings
from core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


# ── Password hashing ──────────────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_returns_non_empty_string(self):
        hashed = hash_password("mysecretpassword")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_is_not_plaintext(self):
        pw = "mysecretpassword"
        assert hash_password(pw) != pw

    def test_verify_correct_password(self):
        pw = "correcthorsebatterystaple"
        assert verify_password(pw, hash_password(pw)) is True

    def test_verify_wrong_password(self):
        assert verify_password("wrong", hash_password("right")) is False

    def test_two_hashes_of_same_password_differ(self):
        """Bcrypt salts are random — same password produces different hashes."""
        pw = "samepassword"
        assert hash_password(pw) != hash_password(pw)


# ── Access token ──────────────────────────────────────────────────────────────

class TestAccessToken:
    def test_create_and_decode(self):
        token = create_access_token("user-123", role="user")
        payload = decode_access_token(token)

        assert payload["sub"] == "user-123"
        assert payload["role"] == "user"
        assert payload["type"] == "access"
        assert "jti" in payload

    def test_token_is_valid_jwt_string(self):
        token = create_access_token("user-abc", role="user")
        assert isinstance(token, str)
        assert token.count(".") == 2  # header.payload.signature

    def test_extra_claims_included(self):
        token = create_access_token("u1", role="admin", extra_claims={"org": "acme"})
        payload = decode_access_token(token)
        assert payload["org"] == "acme"

    def test_expiry_is_in_future(self):
        token = create_access_token("u1", role="user")
        payload = decode_token(token)
        exp = payload["exp"]
        assert exp > datetime.now(UTC).timestamp()

    def test_expired_token_raises(self):
        """Forge an already-expired token."""
        now = datetime.now(UTC)
        payload = {
            "sub": "u1",
            "role": "user",
            "jti": "test-jti",
            "iat": now - timedelta(minutes=30),
            "exp": now - timedelta(minutes=1),
            "type": "access",
        }
        expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        with pytest.raises(JWTError):
            decode_access_token(expired_token)

    def test_tampered_signature_raises(self):
        token = create_access_token("u1", role="user")
        # Flip last char in the signature segment
        parts = token.split(".")
        parts[2] = parts[2][:-1] + ("A" if parts[2][-1] != "A" else "B")
        tampered = ".".join(parts)
        with pytest.raises(JWTError):
            decode_access_token(tampered)

    def test_wrong_key_raises(self):
        token = jwt.encode({"sub": "u1", "type": "access"}, "wrong_key", algorithm="HS256")
        with pytest.raises(JWTError):
            decode_access_token(token)

    def test_refresh_token_rejected_as_access(self):
        refresh = create_refresh_token("u1")
        with pytest.raises(JWTError, match="Expected access token"):
            decode_access_token(refresh)


# ── Refresh token ─────────────────────────────────────────────────────────────

class TestRefreshToken:
    def test_create_and_decode(self):
        token = create_refresh_token("user-456")
        payload = decode_refresh_token(token)

        assert payload["sub"] == "user-456"
        assert payload["type"] == "refresh"
        assert "jti" in payload

    def test_expiry_longer_than_access(self):
        access = create_access_token("u1", role="user")
        refresh = create_refresh_token("u1")

        access_exp = decode_token(access)["exp"]
        refresh_exp = decode_token(refresh)["exp"]

        assert refresh_exp > access_exp

    def test_access_token_rejected_as_refresh(self):
        access = create_access_token("u1", role="user")
        with pytest.raises(JWTError, match="Expected refresh token"):
            decode_refresh_token(access)

    def test_unique_jti_per_token(self):
        """Every token gets a unique JTI — required for eventual revocation."""
        t1 = decode_token(create_refresh_token("u1"))["jti"]
        t2 = decode_token(create_refresh_token("u1"))["jti"]
        assert t1 != t2
