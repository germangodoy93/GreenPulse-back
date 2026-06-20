"""Business logic for alert management."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.alerts.models.alert import Alert, AlertSeverity
from src.modules.alerts.repositories.alert_repository import IAlertRepository
from src.modules.devices.repositories.device_repository import IDeviceRepository
from src.shared.exceptions.domain import ConflictException, ForbiddenException, NotFoundException


class AlertService:
    def __init__(
        self,
        alert_repo: IAlertRepository,
        device_repo: IDeviceRepository,
    ) -> None:
        self._alerts = alert_repo
        self._devices = device_repo

    async def list_alerts(
        self,
        session: AsyncSession,
        *,
        propietario_id: int,
        device_id: int | None,
        resuelta: bool | None,
        severity: AlertSeverity | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Alert], int]:
        device_ids = await self._devices.get_ids_by_owner(session, propietario_id)
        if device_id is not None and device_id not in device_ids:
            raise ForbiddenException("No tienes permisos sobre ese dispositivo.")
        return await self._alerts.find_all(
            session,
            device_ids=device_ids,
            device_id=device_id,
            resuelta=resuelta,
            severity=severity,
            offset=offset,
            limit=limit,
        )

    async def get_by_id(
        self, session: AsyncSession, alert_id: int, *, propietario_id: int
    ) -> Alert:
        alert = await self._alerts.get_by_id(session, alert_id)
        if alert is None:
            raise NotFoundException("alerta", alert_id)
        device_ids = await self._devices.get_ids_by_owner(session, propietario_id)
        if alert.device_id not in device_ids:
            raise ForbiddenException("No tienes permisos sobre esa alerta.")
        return alert

    async def resolve(
        self, session: AsyncSession, alert_id: int, *, propietario_id: int
    ) -> Alert:
        alert = await self.get_by_id(session, alert_id, propietario_id=propietario_id)
        if alert.resuelta:
            raise ConflictException(
                message="La alerta ya está resuelta.",
                code="ALERT_ALREADY_RESOLVED",
            )
        alert.resuelta = True
        alert.resolved_at = datetime.now(UTC)
        return await self._alerts.save(session, alert)
