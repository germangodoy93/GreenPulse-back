"""Integration tests for the /api/v1/health endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    """GET /health must return HTTP 200."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_envelope(client: AsyncClient) -> None:
    """Response must conform to the standard SuccessResponse envelope."""
    response = await client.get("/api/v1/health")
    body = response.json()

    assert body["success"] is True
    assert "data" in body
    assert "message" in body
    assert "timestamp" in body


@pytest.mark.asyncio
async def test_health_data_fields(client: AsyncClient) -> None:
    """Data payload must include status, version and environment."""
    response = await client.get("/api/v1/health")
    data = response.json()["data"]

    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_health_security_headers(client: AsyncClient) -> None:
    """SecurityHeadersMiddleware must inject X-Frame-Options on every response."""
    response = await client.get("/api/v1/health")
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("x-content-type-options") == "nosniff"
