"""SQLAlchemy ORM model for the devices table."""

import enum
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.base import Base


class TipoZona(str, enum.Enum):
    interior = "interior"
    exterior = "exterior"
    invernadero = "invernadero"
    bodega = "bodega"


class Device(Base):
    """ESP32 sensor node registered in the system.

    The plain-text API key is NEVER stored — only the bcrypt hash.
    """

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo_zona: Mapped[TipoZona] = mapped_column(
        SAEnum(TipoZona, name="tipozona", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    latitud: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitud: Mapped[float | None] = mapped_column(Float, nullable=True)
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    propietario_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<Device id={self.id} nombre={self.nombre!r} activo={self.activo}>"
