"""Integration tests for the Readings endpoints."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient


# ── helpers ───────────────────────────────────────────────────────────────────

async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Password1"})
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password1"})
    return resp.json()["data"]["access_token"]


async def _create_device(client: AsyncClient, token: str) -> tuple[int, str]:
    resp = await client.post(
        "/api/v1/devices",
        json={"nombre": "ESP32-Test", "tipo_zona": "interior"},
        headers={"Authorization": f"Bearer {token}"},
    )
    data = resp.json()["data"]
    return data["id"], data["api_key"]


def _jwt(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _api_key(key: str) -> dict:
    return {"X-API-Key": key}


READING_PAYLOAD = {
    "recorded_at": datetime.now(UTC).isoformat(),
    "temperature": 22.5,
    "air_humidity": 60.0,
    "soil_humidity": 45.0,
    "pressure": 1013.25,
    "light_lux": 800.0,
}


# ── POST /readings ────────────────────────────────────────────────────────────

async def test_ingest_reading_returns_201(client: AsyncClient) -> None:
    token = await _register_and_login(client, "ingest@test.com")
    _, api_key = await _create_device(client, token)

    resp = await client.post("/api/v1/readings", json=READING_PAYLOAD, headers=_api_key(api_key))

    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["temperature"] == 22.5
    assert data["soil_humidity"] == 45.0


async def test_ingest_reading_without_api_key_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/readings", json=READING_PAYLOAD)
    assert resp.status_code == 401


async def test_ingest_reading_invalid_api_key_returns_401(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/readings",
        json=READING_PAYLOAD,
        headers={"X-API-Key": "invalid-key"},
    )
    assert resp.status_code == 401


async def test_ingest_reading_partial_sensors(client: AsyncClient) -> None:
    token = await _register_and_login(client, "partial@test.com")
    _, api_key = await _create_device(client, token)

    resp = await client.post(
        "/api/v1/readings",
        json={"recorded_at": datetime.now(UTC).isoformat(), "temperature": 25.0},
        headers=_api_key(api_key),
    )

    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["temperature"] == 25.0
    assert data["soil_humidity"] is None


# ── POST /readings/batch ──────────────────────────────────────────────────────

async def test_batch_ingest_returns_201(client: AsyncClient) -> None:
    token = await _register_and_login(client, "batch@test.com")
    _, api_key = await _create_device(client, token)

    batch = {
        "batch_id": "550e8400-e29b-41d4-a716-446655440000",
        "readings": [
            {"recorded_at": datetime.now(UTC).isoformat(), "temperature": 20.0},
            {"recorded_at": datetime.now(UTC).isoformat(), "temperature": 21.0},
        ],
    }
    resp = await client.post("/api/v1/readings/batch", json=batch, headers=_api_key(api_key))

    assert resp.status_code == 201
    assert resp.json()["data"]["inserted"] == 2
    assert resp.json()["data"]["skipped"] is False


async def test_batch_idempotent_on_retry(client: AsyncClient) -> None:
    token = await _register_and_login(client, "idempotent@test.com")
    _, api_key = await _create_device(client, token)

    batch = {
        "batch_id": "idempotent-uuid-1234",
        "readings": [{"recorded_at": datetime.now(UTC).isoformat(), "temperature": 20.0}],
    }
    await client.post("/api/v1/readings/batch", json=batch, headers=_api_key(api_key))
    resp2 = await client.post("/api/v1/readings/batch", json=batch, headers=_api_key(api_key))

    assert resp2.status_code == 201
    assert resp2.json()["data"]["skipped"] is True
    assert resp2.json()["data"]["inserted"] == 0


# ── GET /readings ─────────────────────────────────────────────────────────────

async def test_list_readings_requires_jwt(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/readings")
    assert resp.status_code == 401


async def test_list_readings_returns_200(client: AsyncClient) -> None:
    token = await _register_and_login(client, "list-readings@test.com")
    _, api_key = await _create_device(client, token)
    await client.post("/api/v1/readings", json=READING_PAYLOAD, headers=_api_key(api_key))

    resp = await client.get("/api/v1/readings", headers=_jwt(token))

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["meta"]["total"] >= 1


# ── GET /readings/latest ──────────────────────────────────────────────────────

async def test_get_latest_returns_200(client: AsyncClient) -> None:
    token = await _register_and_login(client, "latest@test.com")
    _, api_key = await _create_device(client, token)
    await client.post("/api/v1/readings", json=READING_PAYLOAD, headers=_api_key(api_key))

    resp = await client.get("/api/v1/readings/latest", headers=_jwt(token))

    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 1


# ── GET /readings/{id} ────────────────────────────────────────────────────────

async def test_get_reading_by_id(client: AsyncClient) -> None:
    token = await _register_and_login(client, "getreading@test.com")
    _, api_key = await _create_device(client, token)
    create_resp = await client.post("/api/v1/readings", json=READING_PAYLOAD, headers=_api_key(api_key))
    reading_id = create_resp.json()["data"]["id"]

    resp = await client.get(f"/api/v1/readings/{reading_id}", headers=_jwt(token))

    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == reading_id


async def test_get_reading_not_found(client: AsyncClient) -> None:
    token = await _register_and_login(client, "readingnotfound@test.com")
    resp = await client.get("/api/v1/readings/99999", headers=_jwt(token))
    assert resp.status_code == 404


# ── GET /readings/aggregate ───────────────────────────────────────────────────

async def test_aggregate_returns_stats(client: AsyncClient) -> None:
    token = await _register_and_login(client, "aggregate@test.com")
    _, api_key = await _create_device(client, token)
    await client.post("/api/v1/readings", json=READING_PAYLOAD, headers=_api_key(api_key))

    resp = await client.get(
        "/api/v1/readings/aggregate",
        params={"field": "temperature"},
        headers=_jwt(token),
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["field"] == "temperature"
    assert data["count"] >= 1
    assert data["avg"] is not None


async def test_aggregate_invalid_field_returns_422(client: AsyncClient) -> None:
    token = await _register_and_login(client, "agginvalid@test.com")

    resp = await client.get(
        "/api/v1/readings/aggregate",
        params={"field": "invalid_sensor"},
        headers=_jwt(token),
    )

    assert resp.status_code == 422
