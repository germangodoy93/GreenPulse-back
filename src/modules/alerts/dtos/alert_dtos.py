"""DTOs for the Alerts module."""

from datetime import datetime

from pydantic import BaseModel

from src.modules.alerts.models.alert import AlertSeverity


class AlertResponse(BaseModel):
    id: int
    device_id: int
    reading_id: int
    field: str
    value: float
    threshold_min: float | None
    threshold_max: float | None
    severity: AlertSeverity
    resuelta: bool
    created_at: datetime
    resolved_at: datetime | None

    model_config = {"from_attributes": True}
