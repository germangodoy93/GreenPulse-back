"""DTOs for the Devices module."""

from datetime import datetime

from pydantic import BaseModel, Field

from src.modules.devices.models.device import TipoZona


class CreateDeviceRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100, examples=["Nodo Invernadero A1"])
    tipo_zona: TipoZona
    latitud: float | None = Field(None, ge=-90, le=90, examples=[4.7110])
    longitud: float | None = Field(None, ge=-180, le=180, examples=[-74.0721])


class UpdateDeviceRequest(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=100)
    tipo_zona: TipoZona | None = None
    latitud: float | None = Field(None, ge=-90, le=90)
    longitud: float | None = Field(None, ge=-180, le=180)


class DeviceResponse(BaseModel):
    id: int
    nombre: str
    tipo_zona: TipoZona
    latitud: float | None
    longitud: float | None
    activo: bool
    propietario_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DeviceCreatedResponse(DeviceResponse):
    """Returned only on creation or key rotation — includes the plain-text API key."""

    api_key: str
