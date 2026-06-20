"""SQLAlchemy ORM model for sensor readings from ESP32 nodes."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class Reading(Base):
    """Single telemetry snapshot from an ESP32 sensor node.

    All sensor columns are nullable: a node may not have every sensor.
    recorded_at is the device-side timestamp; created_at is the server receipt time.
    batch_id allows idempotent batch submissions — retried batches are skipped.
    """

    __tablename__ = "readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    batch_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    # ── Sensor values ─────────────────────────────────────────────────────────
    soil_humidity: Mapped[float | None] = mapped_column(Float, nullable=True)   # % (0-100)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)     # °C (AHT20)
    air_humidity: Mapped[float | None] = mapped_column(Float, nullable=True)    # % (AHT20)
    pressure: Mapped[float | None] = mapped_column(Float, nullable=True)        # hPa (BMP280)
    altitude: Mapped[float | None] = mapped_column(Float, nullable=True)        # m (BMP280)
    light_lux: Mapped[float | None] = mapped_column(Float, nullable=True)       # lux (BH1750)
    water_level: Mapped[float | None] = mapped_column(Float, nullable=True)     # cm (HC-SR04)

    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<Reading id={self.id} device_id={self.device_id} recorded_at={self.recorded_at}>"
