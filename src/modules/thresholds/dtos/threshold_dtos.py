"""DTOs for the Thresholds module."""

from datetime import datetime

from pydantic import BaseModel, Field


class ThresholdUpdate(BaseModel):
    """All fields optional — send only the limits you want to set or clear."""

    soil_humidity_min: float | None = Field(None, ge=0, le=100)
    soil_humidity_max: float | None = Field(None, ge=0, le=100)
    temperature_min: float | None = Field(None, ge=-40, le=85)
    temperature_max: float | None = Field(None, ge=-40, le=85)
    air_humidity_min: float | None = Field(None, ge=0, le=100)
    air_humidity_max: float | None = Field(None, ge=0, le=100)
    pressure_min: float | None = Field(None, ge=300, le=1100)
    pressure_max: float | None = Field(None, ge=300, le=1100)
    altitude_min: float | None = None
    altitude_max: float | None = None
    light_lux_min: float | None = Field(None, ge=0)
    light_lux_max: float | None = Field(None, ge=0)
    water_level_min: float | None = Field(None, ge=0)
    water_level_max: float | None = Field(None, ge=0)


class ThresholdResponse(BaseModel):
    id: int
    device_id: int
    soil_humidity_min: float | None
    soil_humidity_max: float | None
    temperature_min: float | None
    temperature_max: float | None
    air_humidity_min: float | None
    air_humidity_max: float | None
    pressure_min: float | None
    pressure_max: float | None
    altitude_min: float | None
    altitude_max: float | None
    light_lux_min: float | None
    light_lux_max: float | None
    water_level_min: float | None
    water_level_max: float | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
