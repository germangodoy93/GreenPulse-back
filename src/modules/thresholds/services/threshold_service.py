"""Business logic for threshold configuration."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.devices.repositories.device_repository import IDeviceRepository
from src.modules.thresholds.dtos.threshold_dtos import ThresholdUpdate
from src.modules.thresholds.models.threshold import Threshold
from src.modules.thresholds.repositories.threshold_repository import IThresholdRepository
from src.shared.exceptions.domain import ForbiddenException, NotFoundException


class ThresholdService:
    def __init__(
        self,
        threshold_repo: IThresholdRepository,
        device_repo: IDeviceRepository,
    ) -> None:
        self._thresholds = threshold_repo
        self._devices = device_repo

    async def _assert_ownership(
        self, session: AsyncSession, device_id: int, propietario_id: int
    ) -> None:
        device = await self._devices.get_by_id(session, device_id)
        if device is None or not device.activo:
            raise NotFoundException("dispositivo", device_id)
        if device.propietario_id != propietario_id:
            raise ForbiddenException("No tienes permisos sobre este dispositivo.")

    async def get(
        self,
        session: AsyncSession,
        device_id: int,
        *,
        propietario_id: int,
    ) -> Threshold | None:
        await self._assert_ownership(session, device_id, propietario_id)
        return await self._thresholds.get_by_device_id(session, device_id)

    async def upsert(
        self,
        session: AsyncSession,
        device_id: int,
        *,
        data: ThresholdUpdate,
        propietario_id: int,
    ) -> Threshold:
        await self._assert_ownership(session, device_id, propietario_id)
        return await self._thresholds.upsert(
            session,
            device_id=device_id,
            **data.model_dump(),
        )
