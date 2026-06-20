"""Unit tests for ReadingService — all repos mocked with AsyncMock."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.devices.models.device import Device, TipoZona
from src.modules.readings.dtos.reading_dtos import (
    AggregateResponse,
    BatchReadingRequest,
    CreateReadingRequest,
)
from src.modules.readings.models.reading import Reading
from src.modules.readings.services.reading_service import ReadingService
from src.shared.exceptions.domain import ForbiddenException, NotFoundException, ValidationException


def _make_device(id: int = 1, propietario_id: int = 42) -> Device:
    d = Device(
        nombre="Test",
        tipo_zona=TipoZona.interior,
        latitud=None,
        longitud=None,
        api_key_hash="hash",
        activo=True,
        propietario_id=propietario_id,
    )
    d.id = id
    return d


def _make_reading(id: int = 1, device_id: int = 1) -> Reading:
    r = Reading(
        device_id=device_id,
        batch_id=None,
        soil_humidity=45.0,
        temperature=22.5,
        air_humidity=60.0,
        pressure=1013.0,
        altitude=120.0,
        light_lux=800.0,
        water_level=5.0,
        recorded_at=datetime.now(UTC),
    )
    r.id = id
    r.created_at = datetime.now(UTC)
    return r


def _create_req(**kwargs) -> CreateReadingRequest:
    defaults = {"recorded_at": datetime.now(UTC), "temperature": 22.5}
    defaults.update(kwargs)
    return CreateReadingRequest(**defaults)


@pytest.fixture()
def reading_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def device_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def service(reading_repo: AsyncMock, device_repo: AsyncMock) -> ReadingService:
    return ReadingService(reading_repo, device_repo)


@pytest.fixture()
def session() -> MagicMock:
    return MagicMock()


# ── ingest ────────────────────────────────────────────────────────────────────

async def test_ingest_creates_reading(service: ReadingService, reading_repo: AsyncMock, session: MagicMock) -> None:
    device = _make_device()
    reading_repo.create.return_value = _make_reading()

    result = await service.ingest(session, device=device, data=_create_req())

    assert result.id == 1
    reading_repo.create.assert_awaited_once()


async def test_ingest_passes_device_id(service: ReadingService, reading_repo: AsyncMock, session: MagicMock) -> None:
    device = _make_device(id=7)
    created = _make_reading(device_id=7)
    reading_repo.create.return_value = created

    await service.ingest(session, device=device, data=_create_req())

    call_arg = reading_repo.create.call_args.kwargs["reading"]
    assert call_arg.device_id == 7


# ── ingest_batch ──────────────────────────────────────────────────────────────

async def test_batch_skips_duplicate(service: ReadingService, reading_repo: AsyncMock, session: MagicMock) -> None:
    reading_repo.exists_batch.return_value = True
    device = _make_device()
    data = BatchReadingRequest(batch_id="uuid-1", readings=[_create_req()])

    readings, already_existed = await service.ingest_batch(session, device=device, data=data)

    assert already_existed is True
    assert readings == []
    reading_repo.create_bulk.assert_not_awaited()


async def test_batch_inserts_new_readings(service: ReadingService, reading_repo: AsyncMock, session: MagicMock) -> None:
    reading_repo.exists_batch.return_value = False
    reading_repo.create_bulk.return_value = [_make_reading(), _make_reading(id=2)]
    device = _make_device()
    data = BatchReadingRequest(
        batch_id="uuid-2",
        readings=[_create_req(), _create_req(temperature=25.0)],
    )

    readings, already_existed = await service.ingest_batch(session, device=device, data=data)

    assert already_existed is False
    assert len(readings) == 2


# ── list ──────────────────────────────────────────────────────────────────────

async def test_list_returns_filtered_readings(service: ReadingService, reading_repo: AsyncMock, device_repo: AsyncMock, session: MagicMock) -> None:
    device_repo.get_ids_by_owner.return_value = [1, 2]
    reading_repo.find_all.return_value = ([_make_reading()], 1)

    readings, total = await service.list_readings(
        session,
        propietario_id=42,
        device_id=None,
        start_date=None,
        end_date=None,
        offset=0,
        limit=20,
    )

    assert total == 1
    assert len(readings) == 1


async def test_list_rejects_foreign_device(service: ReadingService, device_repo: AsyncMock, session: MagicMock) -> None:
    device_repo.get_ids_by_owner.return_value = [1, 2]

    with pytest.raises(ForbiddenException):
        await service.list_readings(session, propietario_id=42, device_id=99, start_date=None, end_date=None, offset=0, limit=20)


# ── get_by_id ─────────────────────────────────────────────────────────────────

async def test_get_by_id_returns_reading(service: ReadingService, reading_repo: AsyncMock, device_repo: AsyncMock, session: MagicMock) -> None:
    device_repo.get_ids_by_owner.return_value = [1]
    reading_repo.get_by_id.return_value = _make_reading(device_id=1)

    result = await service.get_by_id(session, 1, propietario_id=42)

    assert result.id == 1


async def test_get_by_id_not_found(service: ReadingService, reading_repo: AsyncMock, device_repo: AsyncMock, session: MagicMock) -> None:
    reading_repo.get_by_id.return_value = None

    with pytest.raises(NotFoundException):
        await service.get_by_id(session, 99, propietario_id=42)


async def test_get_by_id_foreign_device_raises_forbidden(service: ReadingService, reading_repo: AsyncMock, device_repo: AsyncMock, session: MagicMock) -> None:
    device_repo.get_ids_by_owner.return_value = [5]
    reading_repo.get_by_id.return_value = _make_reading(device_id=99)

    with pytest.raises(ForbiddenException):
        await service.get_by_id(session, 1, propietario_id=42)


# ── aggregate ─────────────────────────────────────────────────────────────────

async def test_aggregate_valid_field(service: ReadingService, reading_repo: AsyncMock, device_repo: AsyncMock, session: MagicMock) -> None:
    device_repo.get_ids_by_owner.return_value = [1]
    reading_repo.aggregate.return_value = {"avg": 22.5, "min": 20.0, "max": 25.0, "count": 10}

    result = await service.aggregate(
        session,
        propietario_id=42,
        field="temperature",
        device_id=None,
        start_date=None,
        end_date=None,
    )

    assert isinstance(result, AggregateResponse)
    assert result.avg == 22.5
    assert result.count == 10


async def test_aggregate_invalid_field_raises(service: ReadingService, device_repo: AsyncMock, session: MagicMock) -> None:
    device_repo.get_ids_by_owner.return_value = [1]

    with pytest.raises(ValidationException):
        await service.aggregate(
            session,
            propietario_id=42,
            field="invalid_field",
            device_id=None,
            start_date=None,
            end_date=None,
        )
