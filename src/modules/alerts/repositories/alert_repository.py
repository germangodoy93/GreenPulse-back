"""Alert repository: interface + SQLAlchemy implementation."""

from abc import ABC, abstractmethod

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.alerts.models.alert import Alert, AlertSeverity


class IAlertRepository(ABC):
    @abstractmethod
    async def create(self, session: AsyncSession, *, alert: Alert) -> Alert: ...

    @abstractmethod
    async def get_by_id(self, session: AsyncSession, alert_id: int) -> Alert | None: ...

    @abstractmethod
    async def find_all(
        self,
        session: AsyncSession,
        *,
        device_ids: list[int],
        device_id: int | None,
        resuelta: bool | None,
        severity: AlertSeverity | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Alert], int]: ...

    @abstractmethod
    async def save(self, session: AsyncSession, alert: Alert) -> Alert: ...


class SQLAlchemyAlertRepository(IAlertRepository):
    async def create(self, session: AsyncSession, *, alert: Alert) -> Alert:
        session.add(alert)
        await session.flush()
        await session.refresh(alert)
        return alert

    async def get_by_id(self, session: AsyncSession, alert_id: int) -> Alert | None:
        result = await session.execute(select(Alert).where(Alert.id == alert_id))
        return result.scalar_one_or_none()

    async def find_all(
        self,
        session: AsyncSession,
        *,
        device_ids: list[int],
        device_id: int | None,
        resuelta: bool | None,
        severity: AlertSeverity | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Alert], int]:
        allowed_ids = [device_id] if device_id is not None else device_ids
        stmt = select(Alert).where(Alert.device_id.in_(allowed_ids))
        if resuelta is not None:
            stmt = stmt.where(Alert.resuelta.is_(resuelta))
        if severity is not None:
            stmt = stmt.where(Alert.severity == severity)

        count_result = await session.execute(
            select(func.count()).select_from(stmt.subquery())
        )
        total = count_result.scalar_one()

        rows = await session.execute(
            stmt.order_by(Alert.created_at.desc()).offset(offset).limit(limit)
        )
        return list(rows.scalars().all()), total

    async def save(self, session: AsyncSession, alert: Alert) -> Alert:
        session.add(alert)
        await session.flush()
        await session.refresh(alert)
        return alert
