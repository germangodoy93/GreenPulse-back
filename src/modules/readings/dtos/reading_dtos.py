"""DTOs for the Readings module."""

from datetime import datetime

from pydantic import BaseModel, Field


class CreateReadingRequest(BaseModel):
    batch_id: str | None = Field(None, max_length=36, description="UUID v4 para idempotencia en reintentos")
    recorded_at: datetime = Field(..., description="Timestamp del dispositivo (ISO 8601 con timezone)")

    # ── Sensor fields (all optional — node may not have every sensor) ─────────
    soil_humidity: float | None = Field(None, ge=0, le=100, description="Humedad del suelo %")
    temperature: float | None = Field(None, ge=-40, le=85, description="Temperatura °C (AHT20)")
    air_humidity: float | None = Field(None, ge=0, le=100, description="Humedad relativa % (AHT20)")
    pressure: float | None = Field(None, ge=300, le=1100, description="Presión hPa (BMP280)")
    altitude: float | None = Field(None, description="Altitud m (BMP280)")
    light_lux: float | None = Field(None, ge=0, description="Luminosidad lux (BH1750)")
    water_level: float | None = Field(None, ge=0, description="Nivel de agua cm (HC-SR04)")


class BatchReadingRequest(BaseModel):
    batch_id: str = Field(..., max_length=36, description="UUID v4 del lote — garantiza idempotencia")
    readings: list[CreateReadingRequest] = Field(..., min_length=1, max_length=100)


class ReadingResponse(BaseModel):
    id: int
    device_id: int
    batch_id: str | None
    soil_humidity: float | None
    temperature: float | None
    air_humidity: float | None
    pressure: float | None
    altitude: float | None
    light_lux: float | None
    water_level: float | None
    recorded_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class AggregateResponse(BaseModel):
    field: str
    device_id: int | None
    count: int
    avg: float | None
    min: float | None
    max: float | None
    start_date: datetime | None
    end_date: datetime | None
