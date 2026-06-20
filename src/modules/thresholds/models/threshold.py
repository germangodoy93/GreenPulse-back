"""SQLAlchemy ORM model for device threshold configuration."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class Threshold(Base):
    """Acceptable value ranges for each sensor field on a device.

    One row per device (enforced by UNIQUE constraint on device_id).
    All min/max values are nullable — a NULL means "no limit on that side".
    """

    __tablename__ = "thresholds"
    __table_args__ = (UniqueConstraint("device_id", name="uq_thresholds_device_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # ── Sensor limits (all nullable) ──────────────────────────────────────────
    soil_humidity_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    soil_humidity_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    air_humidity_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    air_humidity_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    pressure_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    pressure_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    altitude_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    altitude_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    light_lux_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    light_lux_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    water_level_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    water_level_max: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<Threshold device_id={self.device_id}>"
