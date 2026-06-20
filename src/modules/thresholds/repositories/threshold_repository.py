"""Threshold repository: interface + SQLAlchemy implementation."""

from abc import ABC, abstractmethod

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.thresholds.models.threshold import Threshold


class IThresholdRepository(ABC):
    @abstractmethod
    async def get_by_device_id(
        self, session: AsyncSession, device_id: int
    ) -> Threshold | None: ...

    @abstractmethod
    async def upsert(
        self, session: AsyncSession, *, device_id: int, **fields: float | None
    ) -> Threshold: ...


class SQLAlchemyThresholdRepository(IThresholdRepository):
    async def get_by_device_id(
        self, session: AsyncSession, device_id: int
    ) -> Threshold | None:
        result = await session.execute(
            select(Threshold).where(Threshold.device_id == device_id)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self, session: AsyncSession, *, device_id: int, **fields: float | None
    ) -> Threshold:
        threshold = await self.get_by_device_id(session, device_id)
        if threshold is None:
            threshold = Threshold(device_id=device_id)
            session.add(threshold)
        for key, value in fields.items():
            setattr(threshold, key, value)
        await session.flush()
        await session.refresh(threshold)
        return threshold
