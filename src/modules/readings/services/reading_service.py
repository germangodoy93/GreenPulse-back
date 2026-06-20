"""Business logic for ingesting and querying sensor readings."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.devices.models.device import Device
from src.modules.devices.repositories.device_repository import IDeviceRepository
from src.modules.readings.dtos.reading_dtos import (
    AggregateResponse,
    BatchReadingRequest,
    CreateReadingRequest,
)
from src.modules.readings.models.reading import Reading
from src.modules.readings.repositories.reading_repository import (
    AGGREGATABLE_FIELDS,
    IReadingRepository,
)
from src.shared.exceptions.domain import ForbiddenException, NotFoundException, ValidationException


class ReadingService:
    def __init__(
        self,
        reading_repo: IReadingRepository,
        device_repo: IDeviceRepository,
    ) -> None:
        self._readings = reading_repo
        self._devices = device_repo

    async def ingest(
        self,
        session: AsyncSession,
        *,
        device: Device,
        data: CreateReadingRequest,
    ) -> Reading:
        reading = Reading(
            device_id=device.id,
            batch_id=data.batch_id,
            soil_humidity=data.soil_humidity,
            temperature=data.temperature,
            air_humidity=data.air_humidity,
            pressure=data.pressure,
            altitude=data.altitude,
            light_lux=data.light_lux,
            water_level=data.water_level,
            recorded_at=data.recorded_at,
        )
        return await self._readings.create(session, reading=reading)

    async def ingest_batch(
        self,
        session: AsyncSession,
        *,
        device: Device,
        data: BatchReadingRequest,
    ) -> tuple[list[Reading], bool]:
        """Return (readings, already_existed). If batch_id already in DB, skip."""
        already_existed = await self._readings.exists_batch(session, device.id, data.batch_id)
        if already_existed:
            return [], True

        readings = [
            Reading(
                device_id=device.id,
                batch_id=data.batch_id,
                soil_humidity=r.soil_humidity,
                temperature=r.temperature,
                air_humidity=r.air_humidity,
                pressure=r.pressure,
                altitude=r.altitude,
                light_lux=r.light_lux,
                water_level=r.water_level,
                recorded_at=r.recorded_at,
            )
            for r in data.readings
        ]
        saved = await self._readings.create_bulk(session, readings)
        return saved, False

    async def list_readings(
        self,
        session: AsyncSession,
        *,
        propietario_id: int,
        device_id: int | None,
        start_date: datetime | None,
        end_date: datetime | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Reading], int]:
        device_ids = await self._devices.get_ids_by_owner(session, propietario_id)
        if device_id is not None and device_id not in device_ids:
            raise ForbiddenException("No tienes permisos sobre ese dispositivo.")
        return await self._readings.find_all(
            session,
            device_ids=device_ids,
            device_id=device_id,
            start_date=start_date,
            end_date=end_date,
            offset=offset,
            limit=limit,
        )

    async def get_by_id(
        self,
        session: AsyncSession,
        reading_id: int,
        *,
        propietario_id: int,
    ) -> Reading:
        reading = await self._readings.get_by_id(session, reading_id)
        if reading is None:
            raise NotFoundException("lectura", reading_id)
        device_ids = await self._devices.get_ids_by_owner(session, propietario_id)
        if reading.device_id not in device_ids:
            raise ForbiddenException("No tienes permisos sobre esa lectura.")
        return reading

    async def get_latest_per_device(
        self, session: AsyncSession, *, propietario_id: int
    ) -> list[Reading]:
        device_ids = await self._devices.get_ids_by_owner(session, propietario_id)
        return await self._readings.get_latest_per_device(session, device_ids)

    async def aggregate(
        self,
        session: AsyncSession,
        *,
        propietario_id: int,
        field: str,
        device_id: int | None,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> AggregateResponse:
        if field not in AGGREGATABLE_FIELDS:
            raise ValidationException(
                f"Campo '{field}' no es agregable. Valores válidos: {sorted(AGGREGATABLE_FIELDS)}"
            )
        device_ids = await self._devices.get_ids_by_owner(session, propietario_id)
        if device_id is not None and device_id not in device_ids:
            raise ForbiddenException("No tienes permisos sobre ese dispositivo.")

        stats = await self._readings.aggregate(
            session,
            field=field,
            device_ids=device_ids,
            device_id=device_id,
            start_date=start_date,
            end_date=end_date,
        )
        return AggregateResponse(
            field=field,
            device_id=device_id,
            count=stats["count"],
            avg=stats["avg"],
            min=stats["min"],
            max=stats["max"],
            start_date=start_date,
            end_date=end_date,
        )
