"""Reading repository: interface + SQLAlchemy implementation."""

from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.readings.models.reading import Reading


# Sensor fields exposed for aggregate queries
AGGREGATABLE_FIELDS: frozenset[str] = frozenset(
    {"soil_humidity", "temperature", "air_humidity", "pressure", "altitude", "light_lux", "water_level"}
)


class IReadingRepository(ABC):
    @abstractmethod
    async def create(self, session: AsyncSession, *, reading: Reading) -> Reading: ...

    @abstractmethod
    async def create_bulk(
        self, session: AsyncSession, readings: list[Reading]
    ) -> list[Reading]: ...

    @abstractmethod
    async def get_by_id(self, session: AsyncSession, reading_id: int) -> Reading | None: ...

    @abstractmethod
    async def exists_batch(
        self, session: AsyncSession, device_id: int, batch_id: str
    ) -> bool: ...

    @abstractmethod
    async def find_all(
        self,
        session: AsyncSession,
        *,
        device_ids: list[int],
        device_id: int | None,
        start_date: datetime | None,
        end_date: datetime | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Reading], int]: ...

    @abstractmethod
    async def get_latest_per_device(
        self, session: AsyncSession, device_ids: list[int]
    ) -> list[Reading]: ...

    @abstractmethod
    async def aggregate(
        self,
        session: AsyncSession,
        *,
        field: str,
        device_ids: list[int],
        device_id: int | None,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> dict[str, float | int | None]: ...


class SQLAlchemyReadingRepository(IReadingRepository):
    async def create(self, session: AsyncSession, *, reading: Reading) -> Reading:
        session.add(reading)
        await session.flush()
        await session.refresh(reading)
        return reading

    async def create_bulk(
        self, session: AsyncSession, readings: list[Reading]
    ) -> list[Reading]:
        for r in readings:
            session.add(r)
        await session.flush()
        for r in readings:
            await session.refresh(r)
        return readings

    async def get_by_id(self, session: AsyncSession, reading_id: int) -> Reading | None:
        result = await session.execute(select(Reading).where(Reading.id == reading_id))
        return result.scalar_one_or_none()

    async def exists_batch(
        self, session: AsyncSession, device_id: int, batch_id: str
    ) -> bool:
        result = await session.execute(
            select(func.count()).where(
                Reading.device_id == device_id,
                Reading.batch_id == batch_id,
            )
        )
        return result.scalar_one() > 0

    async def find_all(
        self,
        session: AsyncSession,
        *,
        device_ids: list[int],
        device_id: int | None,
        start_date: datetime | None,
        end_date: datetime | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Reading], int]:
        allowed_ids = [device_id] if device_id is not None else device_ids
        stmt = select(Reading).where(Reading.device_id.in_(allowed_ids))
        if start_date:
            stmt = stmt.where(Reading.recorded_at >= start_date)
        if end_date:
            stmt = stmt.where(Reading.recorded_at <= end_date)

        count_result = await session.execute(
            select(func.count()).select_from(stmt.subquery())
        )
        total = count_result.scalar_one()

        rows = await session.execute(
            stmt.order_by(Reading.recorded_at.desc()).offset(offset).limit(limit)
        )
        return list(rows.scalars().all()), total

    async def get_latest_per_device(
        self, session: AsyncSession, device_ids: list[int]
    ) -> list[Reading]:
        if not device_ids:
            return []
        subq = (
            select(Reading.device_id, func.max(Reading.recorded_at).label("max_ts"))
            .where(Reading.device_id.in_(device_ids))
            .group_by(Reading.device_id)
            .subquery()
        )
        result = await session.execute(
            select(Reading).join(
                subq,
                (Reading.device_id == subq.c.device_id)
                & (Reading.recorded_at == subq.c.max_ts),
            )
        )
        return list(result.scalars().all())

    async def aggregate(
        self,
        session: AsyncSession,
        *,
        field: str,
        device_ids: list[int],
        device_id: int | None,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> dict[str, float | int | None]:
        field_col = getattr(Reading, field)
        allowed_ids = [device_id] if device_id is not None else device_ids
        stmt = select(
            func.avg(field_col).label("avg"),
            func.min(field_col).label("min"),
            func.max(field_col).label("max"),
            func.count(field_col).label("count"),
        ).where(Reading.device_id.in_(allowed_ids))
        if start_date:
            stmt = stmt.where(Reading.recorded_at >= start_date)
        if end_date:
            stmt = stmt.where(Reading.recorded_at <= end_date)

        row = (await session.execute(stmt)).one()
        return {
            "avg": float(row.avg) if row.avg is not None else None,
            "min": float(row.min) if row.min is not None else None,
            "max": float(row.max) if row.max is not None else None,
            "count": int(row.count),
        }
