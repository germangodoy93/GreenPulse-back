"""Integration tests for GET/PUT /api/v1/devices/{id}/thresholds."""

import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Password1"})
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password1"})
    return resp.json()["data"]["access_token"]


async def _create_device(client: AsyncClient, token: str) -> int:
    resp = await client.post(
        "/api/v1/devices",
        json={"nombre": "Test Node", "tipo_zona": "interior"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()["data"]["id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


THRESHOLD_PAYLOAD = {
    "temperature_min": 15.0,
    "temperature_max": 35.0,
    "soil_humidity_min": 30.0,
    "soil_humidity_max": 80.0,
    "air_humidity_min": 40.0,
    "air_humidity_max": 90.0,
}


# ── GET /devices/{id}/thresholds ──────────────────────────────────────────────

async def test_get_thresholds_no_config_returns_null(client: AsyncClient) -> None:
    token = await _register_and_login(client, "thresh-get-null@test.com")
    device_id = await _create_device(client, token)

    resp = await client.get(f"/api/v1/devices/{device_id}/thresholds", headers=_auth(token))

    assert resp.status_code == 200
    assert resp.json()["data"] is None


async def test_get_thresholds_returns_401_without_token(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/devices/1/thresholds")
    assert resp.status_code == 401


async def test_get_thresholds_wrong_device_returns_404(client: AsyncClient) -> None:
    token = await _register_and_login(client, "thresh-404@test.com")
    resp = await client.get("/api/v1/devices/99999/thresholds", headers=_auth(token))
    assert resp.status_code == 404


# ── PUT /devices/{id}/thresholds ──────────────────────────────────────────────

async def test_put_thresholds_creates_config(client: AsyncClient) -> None:
    token = await _register_and_login(client, "thresh-put@test.com")
    device_id = await _create_device(client, token)

    resp = await client.put(
        f"/api/v1/devices/{device_id}/thresholds",
        json=THRESHOLD_PAYLOAD,
        headers=_auth(token),
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["temperature_min"] == 15.0
    assert data["temperature_max"] == 35.0
    assert data["device_id"] == device_id


async def test_put_thresholds_updates_existing(client: AsyncClient) -> None:
    token = await _register_and_login(client, "thresh-update@test.com")
    device_id = await _create_device(client, token)

    await client.put(
        f"/api/v1/devices/{device_id}/thresholds",
        json=THRESHOLD_PAYLOAD,
        headers=_auth(token),
    )
    resp2 = await client.put(
        f"/api/v1/devices/{device_id}/thresholds",
        json={"temperature_min": 10.0, "temperature_max": 40.0},
        headers=_auth(token),
    )

    assert resp2.status_code == 200
    assert resp2.json()["data"]["temperature_min"] == 10.0
    assert resp2.json()["data"]["temperature_max"] == 40.0


async def test_put_thresholds_after_get_returns_config(client: AsyncClient) -> None:
    token = await _register_and_login(client, "thresh-roundtrip@test.com")
    device_id = await _create_device(client, token)

    await client.put(
        f"/api/v1/devices/{device_id}/thresholds",
        json=THRESHOLD_PAYLOAD,
        headers=_auth(token),
    )
    resp = await client.get(f"/api/v1/devices/{device_id}/thresholds", headers=_auth(token))

    assert resp.status_code == 200
    assert resp.json()["data"]["temperature_min"] == 15.0


async def test_put_thresholds_other_user_returns_403(client: AsyncClient) -> None:
    token_a = await _register_and_login(client, "thresh-ownerA@test.com")
    token_b = await _register_and_login(client, "thresh-ownerB@test.com")
    device_id = await _create_device(client, token_a)

    resp = await client.put(
        f"/api/v1/devices/{device_id}/thresholds",
        json=THRESHOLD_PAYLOAD,
        headers=_auth(token_b),
    )
    assert resp.status_code == 403


# ── Rules engine integration ──────────────────────────────────────────────────

async def test_reading_above_max_generates_alert(client: AsyncClient) -> None:
    """When a reading violates a configured threshold, the response still returns 201
    (alerts are created silently). Verifies the pipeline does not error out."""
    from datetime import UTC, datetime

    token = await _register_and_login(client, "thresh-alert@test.com")

    # Create device and get API key
    device_resp = await client.post(
        "/api/v1/devices",
        json={"nombre": "Alert Test Node", "tipo_zona": "invernadero"},
        headers=_auth(token),
    )
    device_id = device_resp.json()["data"]["id"]
    api_key = device_resp.json()["data"]["api_key"]

    # Configure threshold: temperature max = 25°C
    await client.put(
        f"/api/v1/devices/{device_id}/thresholds",
        json={"temperature_max": 25.0},
        headers=_auth(token),
    )

    # Send a reading with temperature = 40°C (above max)
    resp = await client.post(
        "/api/v1/readings",
        json={"recorded_at": datetime.now(UTC).isoformat(), "temperature": 40.0},
        headers={"X-API-Key": api_key},
    )

    assert resp.status_code == 201
