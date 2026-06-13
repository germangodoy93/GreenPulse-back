"""Integration tests for the Auth endpoints.

Uses the in-memory SQLite database from conftest.py.
Each test class uses a unique email to avoid conflicts between tests.
"""

import pytest
from httpx import AsyncClient


# ── POST /api/v1/auth/register ────────────────────────────────────────────────

class TestRegisterEndpoint:
    async def test_register_returns_201(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "reg1@test.io", "password": "Segura1234"},
        )
        assert response.status_code == 201

    async def test_register_response_envelope(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "reg2@test.io", "password": "Segura1234"},
        )
        body = response.json()
        assert body["success"] is True
        assert body["data"]["email"] == "reg2@test.io"
        assert "password" not in body["data"]
        assert "password_hash" not in body["data"]

    async def test_register_default_role_is_viewer(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "reg3@test.io", "password": "Segura1234"},
        )
        assert response.json()["data"]["rol"] == "viewer"

    async def test_register_duplicate_email_returns_409(self, client: AsyncClient) -> None:
        payload = {"email": "dup@test.io", "password": "Segura1234"}
        await client.post("/api/v1/auth/register", json=payload)
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "EMAIL_TAKEN"

    async def test_register_weak_password_returns_422(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "reg4@test.io", "password": "weak"},
        )
        assert response.status_code == 422

    async def test_register_invalid_email_returns_422(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "Segura1234"},
        )
        assert response.status_code == 422


# ── POST /api/v1/auth/login ───────────────────────────────────────────────────

class TestLoginEndpoint:
    @pytest.fixture(autouse=True)
    async def _seed_user(self, client: AsyncClient) -> None:
        await client.post(
            "/api/v1/auth/register",
            json={"email": "login@test.io", "password": "Segura1234"},
        )

    async def test_login_returns_200_with_token(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "login@test.io", "password": "Segura1234"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    async def test_login_wrong_password_returns_401(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "login@test.io", "password": "Incorrecta1"},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "UNAUTHORIZED"

    async def test_login_unknown_email_returns_401(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@test.io", "password": "Segura1234"},
        )
        assert response.status_code == 401


# ── GET /api/v1/auth/me ───────────────────────────────────────────────────────

class TestMeEndpoint:
    @pytest.fixture
    async def auth_token(self, client: AsyncClient) -> str:
        await client.post(
            "/api/v1/auth/register",
            json={"email": "me@test.io", "password": "Segura1234"},
        )
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "me@test.io", "password": "Segura1234"},
        )
        return str(resp.json()["data"]["access_token"])

    async def test_me_returns_user_profile(
        self, client: AsyncClient, auth_token: str
    ) -> None:
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["email"] == "me@test.io"

    async def test_me_without_token_returns_401(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_me_with_invalid_token_returns_401(
        self, client: AsyncClient
    ) -> None:
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401
