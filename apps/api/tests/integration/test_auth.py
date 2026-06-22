"""
test_auth.py — Integration tests for the full register → login → refresh cycle.
Requires Testcontainers (real Postgres + Redis).
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestRegister:
    async def test_register_returns_201_and_token(self, client: AsyncClient):
        resp = await client.post("/v1/auth/register", json={
            "email": "alice@example.com",
            "password": "Str0ngPassword!",
        })
        assert resp.status_code == 201
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    async def test_register_sets_refresh_cookie(self, client: AsyncClient):
        resp = await client.post("/v1/auth/register", json={
            "email": "bob@example.com",
            "password": "Str0ngPassword!",
        })
        assert resp.status_code == 201
        assert "refresh_token" in resp.cookies

    async def test_duplicate_email_returns_409(self, client: AsyncClient):
        payload = {"email": "carol@example.com", "password": "pw1234"}
        await client.post("/v1/auth/register", json=payload)
        resp = await client.post("/v1/auth/register", json=payload)
        assert resp.status_code == 409

    async def test_invalid_email_returns_422(self, client: AsyncClient):
        resp = await client.post("/v1/auth/register", json={
            "email": "not-an-email",
            "password": "pw",
        })
        assert resp.status_code == 422


class TestLogin:
    async def test_login_valid_credentials(self, client: AsyncClient):
        # Register first
        email, password = "dave@example.com", "ValidPass123"
        await client.post("/v1/auth/register", json={"email": email, "password": password})

        resp = await client.post("/v1/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_login_wrong_password_returns_401(self, client: AsyncClient):
        email = "eve@example.com"
        await client.post("/v1/auth/register", json={"email": email, "password": "correct"})
        resp = await client.post("/v1/auth/login", json={"email": email, "password": "wrong"})
        assert resp.status_code == 401

    async def test_login_unknown_email_returns_401(self, client: AsyncClient):
        resp = await client.post("/v1/auth/login", json={
            "email": "ghost@example.com",
            "password": "anything",
        })
        assert resp.status_code == 401

    async def test_login_sets_refresh_cookie(self, client: AsyncClient):
        email, pw = "frank@example.com", "SecurePass1"
        await client.post("/v1/auth/register", json={"email": email, "password": pw})
        resp = await client.post("/v1/auth/login", json={"email": email, "password": pw})
        assert "refresh_token" in resp.cookies


class TestRefresh:
    async def test_refresh_returns_new_access_token(self, client: AsyncClient):
        # Register to get refresh cookie
        reg = await client.post("/v1/auth/register", json={
            "email": "grace@example.com",
            "password": "MyPass123",
        })
        assert reg.status_code == 201

        # HTTPX automatically sends cookies from previous response
        resp = await client.post("/v1/auth/refresh")
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body

    async def test_refresh_without_cookie_returns_401(self, client: AsyncClient):
        # Fresh client with no cookies
        from httpx import AsyncClient as FreshClient, ASGITransport
        from main import create_app
        async with FreshClient(transport=ASGITransport(create_app()), base_url="http://test") as fresh:
            resp = await fresh.post("/v1/auth/refresh")
        assert resp.status_code == 401

    async def test_refresh_rotates_cookie(self, client: AsyncClient):
        """Each refresh issues a brand-new refresh token cookie."""
        await client.post("/v1/auth/register", json={
            "email": "heidi@example.com",
            "password": "MyPass123",
        })
        r1 = await client.post("/v1/auth/refresh")
        r2 = await client.post("/v1/auth/refresh")

        # Cookies should be different strings (new JTI)
        assert r1.cookies.get("refresh_token") != r2.cookies.get("refresh_token")


class TestLogout:
    async def test_logout_clears_cookie(self, client: AsyncClient):
        await client.post("/v1/auth/register", json={
            "email": "ivan@example.com",
            "password": "APass123",
        })
        resp = await client.post("/v1/auth/logout")
        assert resp.status_code == 204
        # Cookie should be cleared (max-age=0 or deleted)
        # httpx represents deleted cookies as absent or max-age=0
        cookie = resp.cookies.get("refresh_token")
        assert cookie is None or cookie == ""
