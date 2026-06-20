"""Integration tests for the Devices endpoints."""

import pytest
from httpx import AsyncClient


# ── helpers ───────────────────────────────────────────────────────────────────

async def _register_and_login(client: AsyncClient, email: str = "dev@test.com") -> str:
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Password1"})
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password1"})
    return resp.json()["data"]["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


DEVICE_PAYLOAD = {
    "nombre": "Nodo Invernadero A1",
    "tipo_zona": "invernadero",
    "latitud": 4.711,
    "longitud": -74.072,
}


# ── POST /devices ─────────────────────────────────────────────────────────────

async def test_create_device_returns_201_with_api_key(client: AsyncClient) -> None:
    token = await _register_and_login(client, "create@test.com")
    resp = await client.post("/api/v1/devices", json=DEVICE_PAYLOAD, headers=_auth(token))

    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["nombre"] == "Nodo Invernadero A1"
    assert data["tipo_zona"] == "invernadero"
    assert "api_key" in data
    assert len(data["api_key"]) > 10


async def test_create_device_response_envelope(client: AsyncClient) -> None:
    token = await _register_and_login(client, "envelope@test.com")
    resp = await client.post("/api/v1/devices", json=DEVICE_PAYLOAD, headers=_auth(token))

    body = resp.json()
    assert body["success"] is True
    assert "timestamp" in body
    assert "api_key" in body["data"]


async def test_create_device_without_token_returns_401(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/devices", json=DEVICE_PAYLOAD)
    assert resp.status_code == 401


async def test_create_device_missing_required_fields_returns_422(client: AsyncClient) -> None:
    token = await _register_and_login(client, "missing@test.com")
    resp = await client.post("/api/v1/devices", json={"tipo_zona": "interior"}, headers=_auth(token))
    assert resp.status_code == 422


# ── GET /devices ──────────────────────────────────────────────────────────────

async def test_list_devices_returns_200_with_pagination(client: AsyncClient) -> None:
    token = await _register_and_login(client, "list@test.com")
    await client.post("/api/v1/devices", json=DEVICE_PAYLOAD, headers=_auth(token))

    resp = await client.get("/api/v1/devices", headers=_auth(token))

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    assert "meta" in body
    assert body["meta"]["total"] >= 1


async def test_list_devices_without_token_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/devices")
    assert resp.status_code == 401


# ── GET /devices/{id} ────────────────────────────────────────────────────────

async def test_get_device_by_id_returns_200(client: AsyncClient) -> None:
    token = await _register_and_login(client, "getbyid@test.com")
    create_resp = await client.post("/api/v1/devices", json=DEVICE_PAYLOAD, headers=_auth(token))
    device_id = create_resp.json()["data"]["id"]

    resp = await client.get(f"/api/v1/devices/{device_id}", headers=_auth(token))

    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == device_id


async def test_get_device_not_found_returns_404(client: AsyncClient) -> None:
    token = await _register_and_login(client, "notfound@test.com")
    resp = await client.get("/api/v1/devices/99999", headers=_auth(token))
    assert resp.status_code == 404


async def test_get_device_of_other_user_returns_403(client: AsyncClient) -> None:
    token_a = await _register_and_login(client, "ownerA@test.com")
    token_b = await _register_and_login(client, "ownerB@test.com")

    create_resp = await client.post("/api/v1/devices", json=DEVICE_PAYLOAD, headers=_auth(token_a))
    device_id = create_resp.json()["data"]["id"]

    resp = await client.get(f"/api/v1/devices/{device_id}", headers=_auth(token_b))
    assert resp.status_code == 403


# ── PUT /devices/{id} ────────────────────────────────────────────────────────

async def test_update_device_returns_200(client: AsyncClient) -> None:
    token = await _register_and_login(client, "update@test.com")
    create_resp = await client.post("/api/v1/devices", json=DEVICE_PAYLOAD, headers=_auth(token))
    device_id = create_resp.json()["data"]["id"]

    resp = await client.put(
        f"/api/v1/devices/{device_id}",
        json={"nombre": "Nodo Actualizado", "tipo_zona": "bodega"},
        headers=_auth(token),
    )

    assert resp.status_code == 200
    assert resp.json()["data"]["nombre"] == "Nodo Actualizado"
    assert resp.json()["data"]["tipo_zona"] == "bodega"


# ── DELETE /devices/{id} ─────────────────────────────────────────────────────

async def test_delete_device_returns_204(client: AsyncClient) -> None:
    token = await _register_and_login(client, "delete@test.com")
    create_resp = await client.post("/api/v1/devices", json=DEVICE_PAYLOAD, headers=_auth(token))
    device_id = create_resp.json()["data"]["id"]

    resp = await client.delete(f"/api/v1/devices/{device_id}", headers=_auth(token))
    assert resp.status_code == 204


async def test_deleted_device_not_found_on_get(client: AsyncClient) -> None:
    token = await _register_and_login(client, "deletedget@test.com")
    create_resp = await client.post("/api/v1/devices", json=DEVICE_PAYLOAD, headers=_auth(token))
    device_id = create_resp.json()["data"]["id"]

    await client.delete(f"/api/v1/devices/{device_id}", headers=_auth(token))
    resp = await client.get(f"/api/v1/devices/{device_id}", headers=_auth(token))
    assert resp.status_code == 404


# ── POST /devices/{id}/rotate-key ────────────────────────────────────────────

async def test_rotate_key_returns_new_api_key(client: AsyncClient) -> None:
    token = await _register_and_login(client, "rotate@test.com")
    create_resp = await client.post("/api/v1/devices", json=DEVICE_PAYLOAD, headers=_auth(token))
    data = create_resp.json()["data"]
    device_id = data["id"]
    original_key = data["api_key"]

    resp = await client.post(f"/api/v1/devices/{device_id}/rotate-key", headers=_auth(token))

    assert resp.status_code == 200
    new_key = resp.json()["data"]["api_key"]
    assert new_key != original_key
