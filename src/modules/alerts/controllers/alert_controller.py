"""Alerts HTTP controller — gestión de alertas generadas por el motor de reglas."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.session import get_db
from src.infrastructure.security.dependencies import get_current_user_id
from src.modules.alerts.dtos.alert_dtos import AlertResponse
from src.modules.alerts.models.alert import AlertSeverity
from src.modules.alerts.repositories.alert_repository import (
    IAlertRepository,
    SQLAlchemyAlertRepository,
)
from src.modules.alerts.services.alert_service import AlertService
from src.modules.devices.repositories.device_repository import (
    IDeviceRepository,
    SQLAlchemyDeviceRepository,
)
from src.shared.response.schemas import PaginatedResponse, PaginationMeta, SuccessResponse
from src.shared.utils.pagination import PaginationParams

router = APIRouter(prefix="/alerts", tags=["Alertas"])


def get_alert_service(
    alert_repo: IAlertRepository = Depends(lambda: SQLAlchemyAlertRepository()),
    device_repo: IDeviceRepository = Depends(lambda: SQLAlchemyDeviceRepository()),
) -> AlertService:
    return AlertService(alert_repo, device_repo)


@router.get(
    "",
    response_model=PaginatedResponse[AlertResponse],
    summary="Listar alertas",
    description=(
        "Devuelve las alertas de los dispositivos del usuario, con filtros opcionales. "
        "Las alertas se ordenan de más reciente a más antigua."
    ),
)
async def list_alerts(
    device_id: int | None = Query(None, description="Filtrar por dispositivo"),
    resuelta: bool | None = Query(None, description="true=resueltas, false=pendientes, omitir=todas"),
    severity: AlertSeverity | None = Query(None, description="Filtrar por severidad"),
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    service: AlertService = Depends(get_alert_service),
) -> PaginatedResponse[AlertResponse]:
    alerts, total = await service.list_alerts(
        session,
        propietario_id=user_id,
        device_id=device_id,
        resuelta=resuelta,
        severity=severity,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    return PaginatedResponse(
        data=[AlertResponse.model_validate(a) for a in alerts],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            has_next=(pagination.offset + pagination.limit) < total,
        ),
    )


@router.get(
    "/{alert_id}",
    response_model=SuccessResponse[AlertResponse],
    summary="Obtener alerta por ID",
    responses={
        200: {"description": "Detalle de la alerta"},
        401: {"description": "Token JWT ausente o inválido"},
        403: {"description": "La alerta no pertenece al usuario"},
        404: {"description": "Alerta no encontrada"},
    },
)
async def get_alert(
    alert_id: int,
    session: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    service: AlertService = Depends(get_alert_service),
) -> SuccessResponse[AlertResponse]:
    alert = await service.get_by_id(session, alert_id, propietario_id=user_id)
    return SuccessResponse(
        data=AlertResponse.model_validate(alert),
        message="Alerta encontrada.",
    )


@router.put(
    "/{alert_id}/resolve",
    response_model=SuccessResponse[AlertResponse],
    summary="Resolver alerta",
    description="Marca la alerta como resuelta. No se puede resolver una alerta ya resuelta.",
    responses={
        200: {"description": "Alerta resuelta"},
        401: {"description": "Token JWT ausente o inválido"},
        403: {"description": "La alerta no pertenece al usuario"},
        404: {"description": "Alerta no encontrada"},
        409: {"description": "La alerta ya está resuelta"},
    },
)
async def resolve_alert(
    alert_id: int,
    session: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    service: AlertService = Depends(get_alert_service),
) -> SuccessResponse[AlertResponse]:
    alert = await service.resolve(session, alert_id, propietario_id=user_id)
    return SuccessResponse(
        data=AlertResponse.model_validate(alert),
        message="Alerta resuelta correctamente.",
    )
