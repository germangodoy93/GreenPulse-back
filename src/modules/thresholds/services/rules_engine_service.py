"""Orchestrates threshold evaluation and alert creation after reading ingestion."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.alerts.models.alert import Alert
from src.modules.alerts.repositories.alert_repository import IAlertRepository
from src.modules.readings.models.reading import Reading
from src.modules.thresholds.repositories.threshold_repository import IThresholdRepository
from src.modules.thresholds.rules.engine import RulesEngine
from src.modules.thresholds.rules.strategy import RangeCheckStrategy


class RulesEngineService:
    """Evaluates a reading against device thresholds and persists any violations as alerts."""

    def __init__(
        self,
        threshold_repo: IThresholdRepository,
        alert_repo: IAlertRepository,
    ) -> None:
        self._thresholds = threshold_repo
        self._alerts = alert_repo
        self._engine = RulesEngine(RangeCheckStrategy())

    async def evaluate_and_alert(
        self, session: AsyncSession, reading: Reading
    ) -> list[Alert]:
        """Return the list of alerts generated (empty if no threshold configured)."""
        threshold = await self._thresholds.get_by_device_id(session, reading.device_id)
        if threshold is None:
            return []

        violations = self._engine.evaluate(reading, threshold)
        alerts: list[Alert] = []
        for v in violations:
            alert = Alert(
                device_id=reading.device_id,
                reading_id=reading.id,
                field=v.field,
                value=v.value,
                threshold_min=v.threshold_min,
                threshold_max=v.threshold_max,
                severity=v.severity,
            )
            saved = await self._alerts.create(session, alert=alert)
            alerts.append(saved)
        return alerts
