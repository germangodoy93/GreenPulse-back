"""Unit tests for DeviceService — repository mocked with AsyncMock."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.modules.devices.dtos.device_dtos import CreateDeviceRequest, UpdateDeviceRequest
from src.modules.devices.models.device import Device, TipoZona
from src.modules.devices.services.device_service import DeviceService
from src.shared.exceptions.domain import ForbiddenException, NotFoundException


def _make_device(
    id: int = 1,
    nombre: str = "Nodo Test",
    tipo_zona: TipoZona = TipoZona.interior,
    activo: bool = True,
    propietario_id: int = 42,
    api_key_hash: str = "hashed",
) -> Device:
    d = Device(
        nombre=nombre,
        tipo_zona=tipo_zona,
        latitud=None,
        longitud=None,
        api_key_hash=api_key_hash,
        activo=activo,
        propietario_id=propietario_id,
    )
    d.id = id
    return d


@pytest.fixture()
def repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def service(repo: AsyncMock) -> DeviceService:
    return DeviceService(repo)


@pytest.fixture()
def session() -> MagicMock:
    return MagicMock()


# ── create ────────────────────────────────────────────────────────────────────

async def test_create_returns_device_and_plain_key(service: DeviceService, repo: AsyncMock, session: MagicMock) -> None:
    repo.create.return_value = _make_device()
    data = CreateDeviceRequest(nombre="Nodo A", tipo_zona=TipoZona.invernadero)

    device, plain_key = await service.create(session, data=data, propietario_id=42)

    assert device.nombre == "Nodo Test"
    assert isinstance(plain_key, str) and len(plain_key) > 10
    repo.create.assert_awaited_once()


async def test_create_stores_hash_not_plain_key(service: DeviceService, repo: AsyncMock, session: MagicMock) -> None:
    repo.create.return_value = _make_device()
    data = CreateDeviceRequest(nombre="Nodo B", tipo_zona=TipoZona.exterior)

    _, plain_key = await service.create(session, data=data, propietario_id=42)

    call_kwargs = repo.create.call_args.kwargs
    assert call_kwargs["api_key_hash"] != plain_key


# ── list_by_owner ─────────────────────────────────────────────────────────────

async def test_list_by_owner_delegates_to_repo(service: DeviceService, repo: AsyncMock, session: MagicMock) -> None:
    devices = [_make_device(id=1), _make_device(id=2)]
    repo.get_by_owner.return_value = (devices, 2)

    result, total = await service.list_by_owner(session, propietario_id=42, offset=0, limit=20)

    assert total == 2
    assert len(result) == 2


# ── get_by_id ─────────────────────────────────────────────────────────────────

async def test_get_by_id_returns_device(service: DeviceService, repo: AsyncMock, session: MagicMock) -> None:
    repo.get_by_id.return_value = _make_device(propietario_id=42)

    device = await service.get_by_id(session, 1, propietario_id=42)

    assert device.id == 1


async def test_get_by_id_not_found_raises(service: DeviceService, repo: AsyncMock, session: MagicMock) -> None:
    repo.get_by_id.return_value = None

    with pytest.raises(NotFoundException):
        await service.get_by_id(session, 99, propietario_id=42)


async def test_get_by_id_inactive_raises_not_found(service: DeviceService, repo: AsyncMock, session: MagicMock) -> None:
    repo.get_by_id.return_value = _make_device(activo=False)

    with pytest.raises(NotFoundException):
        await service.get_by_id(session, 1, propietario_id=42)


async def test_get_by_id_wrong_owner_raises_forbidden(service: DeviceService, repo: AsyncMock, session: MagicMock) -> None:
    repo.get_by_id.return_value = _make_device(propietario_id=99)

    with pytest.raises(ForbiddenException):
        await service.get_by_id(session, 1, propietario_id=42)


# ── update ────────────────────────────────────────────────────────────────────

async def test_update_patches_fields(service: DeviceService, repo: AsyncMock, session: MagicMock) -> None:
    original = _make_device(nombre="Viejo", tipo_zona=TipoZona.interior)
    repo.get_by_id.return_value = original
    repo.save.return_value = original

    data = UpdateDeviceRequest(nombre="Nuevo", tipo_zona=TipoZona.bodega)
    device = await service.update(session, 1, data=data, propietario_id=42)

    assert device.nombre == "Nuevo"
    assert device.tipo_zona == TipoZona.bodega


# ── delete ────────────────────────────────────────────────────────────────────

async def test_delete_sets_activo_false(service: DeviceService, repo: AsyncMock, session: MagicMock) -> None:
    device = _make_device()
    repo.get_by_id.return_value = device
    repo.save.return_value = device

    await service.delete(session, 1, propietario_id=42)

    assert device.activo is False
    repo.save.assert_awaited_once()


# ── rotate_key ────────────────────────────────────────────────────────────────

async def test_rotate_key_changes_hash(service: DeviceService, repo: AsyncMock, session: MagicMock) -> None:
    device = _make_device(api_key_hash="old_hash")
    repo.get_by_id.return_value = device
    repo.save.return_value = device

    _, new_plain = await service.rotate_key(session, 1, propietario_id=42)

    assert device.api_key_hash != "old_hash"
    assert isinstance(new_plain, str) and len(new_plain) > 10
