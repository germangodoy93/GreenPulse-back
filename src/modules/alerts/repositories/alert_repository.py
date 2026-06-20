"""Alert repository: interface + SQLAlchemy implementation."""

from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.alerts.models.alert import Alert


class IAlertRepository(ABC):
    @abstractmethod
    async def create(self, session: AsyncSession, *, alert: Alert) -> Alert: ...


class SQLAlchemyAlertRepository(IAlertRepository):
    async def create(self, session: AsyncSession, *, alert: Alert) -> Alert:
        session.add(alert)
        await session.flush()
        await session.refresh(alert)
        return alert
