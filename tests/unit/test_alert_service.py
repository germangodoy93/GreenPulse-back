"""Unit tests for AlertService — repos mocked with AsyncMock."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.alerts.models.alert import Alert, AlertSeverity
from src.modules.alerts.services.alert_service import AlertService
from src.shared.exceptions.domain import ConflictException, ForbiddenException, NotFoundException


def _make_alert(
    id: int = 1,
    device_id: int = 1,
    resuelta: bool = False,
) -> Alert:
    a = Alert(
        device_id=device_id,
        reading_id=1,
        field="temperature",
        value=40.0,
        threshold_min=None,
        threshold_max=35.0,
        severity=AlertSeverity.medium,
        resuelta=resuelta,
    )
    a.id = id
    a.created_at = datetime.now(UTC)
    a.resolved_at = None
    return a


@pytest.fixture()
def alert_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def device_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def service(alert_repo: AsyncMock, device_repo: AsyncMock) -> AlertService:
    return AlertService(alert_repo, device_repo)


@pytest.fixture()
def session() -> MagicMock:
    return MagicMock()


# ── list_alerts ───────────────────────────────────────────────────────────────

async def test_list_alerts_delegates_to_repo(service: AlertService, alert_repo: AsyncMock, device_repo: AsyncMock, session: MagicMock) -> None:
    device_repo.get_ids_by_owner.return_value = [1]
    alert_repo.find_all.return_value = ([_make_alert()], 1)

    alerts, total = await service.list_alerts(
        session, propietario_id=42, device_id=None,
        resuelta=None, severity=None, offset=0, limit=20,
    )

    assert total == 1
    assert len(alerts) == 1


async def test_list_alerts_rejects_foreign_device(service: AlertService, device_repo: AsyncMock, session: MagicMock) -> None:
    device_repo.get_ids_by_owner.return_value = [1, 2]

    with pytest.raises(ForbiddenException):
        await service.list_alerts(
            session, propietario_id=42, device_id=99,
            resuelta=None, severity=None, offset=0, limit=20,
        )


# ── get_by_id ─────────────────────────────────────────────────────────────────

async def test_get_by_id_returns_alert(service: AlertService, alert_repo: AsyncMock, device_repo: AsyncMock, session: MagicMock) -> None:
    device_repo.get_ids_by_owner.return_value = [1]
    alert_repo.get_by_id.return_value = _make_alert(device_id=1)

    result = await service.get_by_id(session, 1, propietario_id=42)
    assert result.id == 1


async def test_get_by_id_not_found_raises(service: AlertService, alert_repo: AsyncMock, session: MagicMock) -> None:
    alert_repo.get_by_id.return_value = None

    with pytest.raises(NotFoundException):
        await service.get_by_id(session, 99, propietario_id=42)


async def test_get_by_id_foreign_device_raises_forbidden(service: AlertService, alert_repo: AsyncMock, device_repo: AsyncMock, session: MagicMock) -> None:
    alert_repo.get_by_id.return_value = _make_alert(device_id=99)
    device_repo.get_ids_by_owner.return_value = [1, 2]

    with pytest.raises(ForbiddenException):
        await service.get_by_id(session, 1, propietario_id=42)


# ── resolve ───────────────────────────────────────────────────────────────────

async def test_resolve_sets_resuelta_true(service: AlertService, alert_repo: AsyncMock, device_repo: AsyncMock, session: MagicMock) -> None:
    alert = _make_alert(resuelta=False)
    alert_repo.get_by_id.return_value = alert
    alert_repo.save.return_value = alert
    device_repo.get_ids_by_owner.return_value = [1]

    result = await service.resolve(session, 1, propietario_id=42)

    assert result.resuelta is True
    assert result.resolved_at is not None


async def test_resolve_already_resolved_raises_conflict(service: AlertService, alert_repo: AsyncMock, device_repo: AsyncMock, session: MagicMock) -> None:
    alert_repo.get_by_id.return_value = _make_alert(resuelta=True)
    device_repo.get_ids_by_owner.return_value = [1]

    with pytest.raises(ConflictException):
        await service.resolve(session, 1, propietario_id=42)
