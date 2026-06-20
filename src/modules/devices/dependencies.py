"""FastAPI dependency for X-API-Key device authentication."""

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.session import get_db
from src.infrastructure.security.api_key import compute_api_key_hash
from src.modules.devices.models.device import Device
from src.modules.devices.repositories.device_repository import SQLAlchemyDeviceRepository
from src.shared.exceptions.domain import UnauthorizedException


async def get_device_by_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    session: AsyncSession = Depends(get_db),
) -> Device:
    """Authenticate an ESP32 node via the X-API-Key header.

    Computes SHA-256 of the incoming key and queries the database directly
    (O(1) with the indexed api_key_hash column).

    Raises:
        UnauthorizedException: If the header is absent or the key is invalid.
    """
    if x_api_key is None:
        raise UnauthorizedException("Header X-API-Key ausente.")
    key_hash = compute_api_key_hash(x_api_key)
    device = await SQLAlchemyDeviceRepository().get_by_api_key_hash(session, key_hash)
    if device is None:
        raise UnauthorizedException("API Key inválida o dispositivo inactivo.")
    return device
