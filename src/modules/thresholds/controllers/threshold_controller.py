"""Thresholds HTTP controller — GET/PUT /api/v1/devices/{device_id}/thresholds."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.session import get_db
from src.infrastructure.security.dependencies import get_current_user_id
from src.modules.devices.repositories.device_repository import (
    IDeviceRepository,
    SQLAlchemyDeviceRepository,
)
from src.modules.thresholds.dtos.threshold_dtos import ThresholdResponse, ThresholdUpdate
from src.modules.thresholds.repositories.threshold_repository import (
    IThresholdRepository,
    SQLAlchemyThresholdRepository,
)
from src.modules.thresholds.services.threshold_service import ThresholdService
from src.shared.response.schemas import SuccessResponse

router = APIRouter(tags=["Umbrales"])


def get_threshold_service(
    threshold_repo: IThresholdRepository = Depends(lambda: SQLAlchemyThresholdRepository()),
    device_repo: IDeviceRepository = Depends(lambda: SQLAlchemyDeviceRepository()),
) -> ThresholdService:
    return ThresholdService(threshold_repo, device_repo)


@router.get(
    "/{device_id}/thresholds",
    response_model=SuccessResponse[ThresholdResponse | None],
    summary="Obtener umbrales del dispositivo",
    description="Devuelve la configuración de umbrales del dispositivo. Retorna `null` si no hay umbrales configurados.",
    responses={
        200: {"description": "Umbrales del dispositivo (null si no configurados)"},
        401: {"description": "Token JWT ausente o inválido"},
        403: {"description": "El dispositivo no pertenece al usuario"},
        404: {"description": "Dispositivo no encontrado"},
    },
)
async def get_thresholds(
    device_id: int,
    session: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    service: ThresholdService = Depends(get_threshold_service),
) -> SuccessResponse[ThresholdResponse | None]:
    threshold = await service.get(session, device_id, propietario_id=user_id)
    data = ThresholdResponse.model_validate(threshold) if threshold else None
    return SuccessResponse(
        data=data,
        message="Umbrales configurados." if threshold else "Sin umbrales configurados.",
    )


@router.put(
    "/{device_id}/thresholds",
    status_code=status.HTTP_200_OK,
    response_model=SuccessResponse[ThresholdResponse],
    summary="Configurar umbrales del dispositivo",
    description=(
        "Crea o actualiza los umbrales de alerta para cada sensor. "
        "Envía `null` en un campo para eliminar ese límite."
    ),
    responses={
        200: {"description": "Umbrales guardados"},
        401: {"description": "Token JWT ausente o inválido"},
        403: {"description": "El dispositivo no pertenece al usuario"},
        404: {"description": "Dispositivo no encontrado"},
    },
)
async def upsert_thresholds(
    device_id: int,
    body: ThresholdUpdate,
    session: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    service: ThresholdService = Depends(get_threshold_service),
) -> SuccessResponse[ThresholdResponse]:
    threshold = await service.upsert(session, device_id, data=body, propietario_id=user_id)
    return SuccessResponse(
        data=ThresholdResponse.model_validate(threshold),
        message="Umbrales guardados correctamente.",
    )
