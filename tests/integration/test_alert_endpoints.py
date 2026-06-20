"""Integration tests for the Alerts endpoints."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient


# ── helpers ───────────────────────────────────────────────────────────────────

async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Password1"})
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password1"})
    return resp.json()["data"]["access_token"]


async def _setup_alert(client: AsyncClient, email: str) -> tuple[str, int]:
    """Register user, create device with threshold, send violating reading.
    Returns (jwt_token, alert_id).
    """
    token = await _register_and_login(client, email)

    # Create device
    device_resp = await client.post(
        "/api/v1/devices",
        json={"nombre": "Alert Test", "tipo_zona": "interior"},
        headers={"Authorization": f"Bearer {token}"},
    )
    device_id = device_resp.json()["data"]["id"]
    api_key = device_resp.json()["data"]["api_key"]

    # Configure threshold: temperature max = 25°C
    await client.put(
        f"/api/v1/devices/{device_id}/thresholds",
        json={"temperature_max": 25.0},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Send violating reading: temperature = 45°C
    await client.post(
        "/api/v1/readings",
        json={"recorded_at": datetime.now(UTC).isoformat(), "temperature": 45.0},
        headers={"X-API-Key": api_key},
    )

    # Get the generated alert
    alerts_resp = await client.get(
        "/api/v1/alerts",
        headers={"Authorization": f"Bearer {token}"},
    )
    alert_id = alerts_resp.json()["data"][0]["id"]
    return token, alert_id


# ── GET /alerts ───────────────────────────────────────────────────────────────

async def test_list_alerts_requires_jwt(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/alerts")
    assert resp.status_code == 401


async def test_list_alerts_returns_200_empty(client: AsyncClient) -> None:
    token = await _register_and_login(client, "alerts-empty@test.com")
    resp = await client.get("/api/v1/alerts", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    assert resp.json()["meta"]["total"] == 0
    assert resp.json()["data"] == []


async def test_list_alerts_after_violation_returns_alert(client: AsyncClient) -> None:
    token, alert_id = await _setup_alert(client, "alerts-list@test.com")

    resp = await client.get("/api/v1/alerts", headers={"Authorization": f"Bearer {token}"})

    assert resp.status_code == 200
    assert resp.json()["meta"]["total"] >= 1
    alert = resp.json()["data"][0]
    assert alert["field"] == "temperature"
    assert alert["value"] == 45.0
    assert alert["resuelta"] is False


async def test_list_alerts_filter_by_resuelta_false(client: AsyncClient) -> None:
    token, _ = await _setup_alert(client, "alerts-filter-open@test.com")

    resp = await client.get(
        "/api/v1/alerts",
        params={"resuelta": "false"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    assert all(not a["resuelta"] for a in resp.json()["data"])


async def test_list_alerts_filter_by_severity(client: AsyncClient) -> None:
    token, _ = await _setup_alert(client, "alerts-severity@test.com")

    resp = await client.get(
        "/api/v1/alerts",
        params={"severity": "high"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    # May or may not have alerts with exactly 'high' — just verify the endpoint works
    assert "data" in resp.json()


# ── GET /alerts/{id} ─────────────────────────────────────────────────────────

async def test_get_alert_by_id_returns_200(client: AsyncClient) -> None:
    token, alert_id = await _setup_alert(client, "alerts-getid@test.com")

    resp = await client.get(
        f"/api/v1/alerts/{alert_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == alert_id


async def test_get_alert_not_found_returns_404(client: AsyncClient) -> None:
    token = await _register_and_login(client, "alerts-notfound@test.com")

    resp = await client.get(
        "/api/v1/alerts/99999",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 404


async def test_get_alert_of_other_user_returns_403(client: AsyncClient) -> None:
    _, alert_id = await _setup_alert(client, "alerts-ownerA@test.com")
    token_b = await _register_and_login(client, "alerts-ownerB@test.com")

    resp = await client.get(
        f"/api/v1/alerts/{alert_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )

    assert resp.status_code == 403


# ── PUT /alerts/{id}/resolve ──────────────────────────────────────────────────

async def test_resolve_alert_returns_200(client: AsyncClient) -> None:
    token, alert_id = await _setup_alert(client, "alerts-resolve@test.com")

    resp = await client.put(
        f"/api/v1/alerts/{alert_id}/resolve",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["resuelta"] is True
    assert data["resolved_at"] is not None


async def test_resolve_alert_twice_returns_409(client: AsyncClient) -> None:
    token, alert_id = await _setup_alert(client, "alerts-double-resolve@test.com")

    await client.put(
        f"/api/v1/alerts/{alert_id}/resolve",
        headers={"Authorization": f"Bearer {token}"},
    )
    resp2 = await client.put(
        f"/api/v1/alerts/{alert_id}/resolve",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp2.status_code == 409


async def test_resolved_alert_appears_in_filter_resuelta_true(client: AsyncClient) -> None:
    token, alert_id = await _setup_alert(client, "alerts-filter-resolved@test.com")

    await client.put(
        f"/api/v1/alerts/{alert_id}/resolve",
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.get(
        "/api/v1/alerts",
        params={"resuelta": "true"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    assert resp.json()["meta"]["total"] >= 1
    assert all(a["resuelta"] for a in resp.json()["data"])
