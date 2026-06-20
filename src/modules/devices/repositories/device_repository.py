"""Device repository: interface (DIP) + SQLAlchemy implementation."""

from abc import ABC, abstractmethod

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.devices.models.device import Device, TipoZona


class IDeviceRepository(ABC):
    @abstractmethod
    async def create(
        self,
        session: AsyncSession,
        *,
        nombre: str,
        tipo_zona: TipoZona,
        latitud: float | None,
        longitud: float | None,
        api_key_hash: str,
        propietario_id: int,
    ) -> Device: ...

    @abstractmethod
    async def get_by_id(self, session: AsyncSession, device_id: int) -> Device | None: ...

    @abstractmethod
    async def get_by_owner(
        self,
        session: AsyncSession,
        propietario_id: int,
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[Device], int]: ...

    @abstractmethod
    async def get_by_api_key_hash(
        self, session: AsyncSession, api_key_hash: str
    ) -> Device | None: ...

    @abstractmethod
    async def get_ids_by_owner(
        self, session: AsyncSession, propietario_id: int
    ) -> list[int]: ...

    @abstractmethod
    async def save(self, session: AsyncSession, device: Device) -> Device: ...


class SQLAlchemyDeviceRepository(IDeviceRepository):
    async def create(
        self,
        session: AsyncSession,
        *,
        nombre: str,
        tipo_zona: TipoZona,
        latitud: float | None,
        longitud: float | None,
        api_key_hash: str,
        propietario_id: int,
    ) -> Device:
        device = Device(
            nombre=nombre,
            tipo_zona=tipo_zona,
            latitud=latitud,
            longitud=longitud,
            api_key_hash=api_key_hash,
            activo=True,
            propietario_id=propietario_id,
        )
        session.add(device)
        await session.flush()
        await session.refresh(device)
        return device

    async def get_by_id(self, session: AsyncSession, device_id: int) -> Device | None:
        result = await session.execute(select(Device).where(Device.id == device_id))
        return result.scalar_one_or_none()

    async def get_by_owner(
        self,
        session: AsyncSession,
        propietario_id: int,
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[Device], int]:
        base_q = select(Device).where(
            Device.propietario_id == propietario_id,
            Device.activo.is_(True),
        )
        count_result = await session.execute(
            select(func.count()).select_from(base_q.subquery())
        )
        total = count_result.scalar_one()

        rows = await session.execute(
            base_q.order_by(Device.created_at.desc()).offset(offset).limit(limit)
        )
        return list(rows.scalars().all()), total

    async def get_by_api_key_hash(
        self, session: AsyncSession, api_key_hash: str
    ) -> Device | None:
        result = await session.execute(
            select(Device).where(
                Device.api_key_hash == api_key_hash,
                Device.activo.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_ids_by_owner(
        self, session: AsyncSession, propietario_id: int
    ) -> list[int]:
        result = await session.execute(
            select(Device.id).where(
                Device.propietario_id == propietario_id,
                Device.activo.is_(True),
            )
        )
        return list(result.scalars().all())

    async def save(self, session: AsyncSession, device: Device) -> Device:
        session.add(device)
        await session.flush()
        await session.refresh(device)
        return device
