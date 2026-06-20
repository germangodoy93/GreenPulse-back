"""Business logic for device management."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.security.api_key import generate_api_key
from src.modules.devices.dtos.device_dtos import CreateDeviceRequest, UpdateDeviceRequest
from src.modules.devices.models.device import Device
from src.modules.devices.repositories.device_repository import IDeviceRepository
from src.shared.exceptions.domain import ForbiddenException, NotFoundException


class DeviceService:
    def __init__(self, repo: IDeviceRepository) -> None:
        self._repo = repo

    async def create(
        self,
        session: AsyncSession,
        *,
        data: CreateDeviceRequest,
        propietario_id: int,
    ) -> tuple[Device, str]:
        plain_key, hashed_key = generate_api_key()
        device = await self._repo.create(
            session,
            nombre=data.nombre,
            tipo_zona=data.tipo_zona,
            latitud=data.latitud,
            longitud=data.longitud,
            api_key_hash=hashed_key,
            propietario_id=propietario_id,
        )
        return device, plain_key

    async def list_by_owner(
        self,
        session: AsyncSession,
        *,
        propietario_id: int,
        offset: int,
        limit: int,
    ) -> tuple[list[Device], int]:
        return await self._repo.get_by_owner(
            session, propietario_id, offset=offset, limit=limit
        )

    async def get_by_id(
        self,
        session: AsyncSession,
        device_id: int,
        *,
        propietario_id: int,
    ) -> Device:
        device = await self._repo.get_by_id(session, device_id)
        if device is None or not device.activo:
            raise NotFoundException("dispositivo", device_id)
        if device.propietario_id != propietario_id:
            raise ForbiddenException("No tienes permisos sobre este dispositivo")
        return device

    async def update(
        self,
        session: AsyncSession,
        device_id: int,
        *,
        data: UpdateDeviceRequest,
        propietario_id: int,
    ) -> Device:
        device = await self.get_by_id(session, device_id, propietario_id=propietario_id)
        if data.nombre is not None:
            device.nombre = data.nombre
        if data.tipo_zona is not None:
            device.tipo_zona = data.tipo_zona
        if data.latitud is not None:
            device.latitud = data.latitud
        if data.longitud is not None:
            device.longitud = data.longitud
        return await self._repo.save(session, device)

    async def delete(
        self,
        session: AsyncSession,
        device_id: int,
        *,
        propietario_id: int,
    ) -> None:
        device = await self.get_by_id(session, device_id, propietario_id=propietario_id)
        device.activo = False
        await self._repo.save(session, device)

    async def rotate_key(
        self,
        session: AsyncSession,
        device_id: int,
        *,
        propietario_id: int,
    ) -> tuple[Device, str]:
        device = await self.get_by_id(session, device_id, propietario_id=propietario_id)
        plain_key, hashed_key = generate_api_key()
        device.api_key_hash = hashed_key
        await self._repo.save(session, device)
        return device, plain_key
