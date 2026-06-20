"""Readings HTTP controller.

Write endpoints (POST) authenticate the ESP32 via X-API-Key.
Read endpoints (GET) require a JWT Bearer token (dashboard user).
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.session import get_db
from src.infrastructure.security.dependencies import get_current_user_id
from src.modules.devices.dependencies import get_device_by_api_key
from src.modules.devices.models.device import Device
from src.modules.devices.repositories.device_repository import (
    IDeviceRepository,
    SQLAlchemyDeviceRepository,
)
from src.modules.readings.dtos.reading_dtos import (
    AggregateResponse,
    BatchReadingRequest,
    CreateReadingRequest,
    ReadingResponse,
)
from src.modules.readings.repositories.reading_repository import (
    IReadingRepository,
    SQLAlchemyReadingRepository,
)
from src.modules.readings.services.reading_service import ReadingService
from src.shared.response.schemas import PaginatedResponse, PaginationMeta, SuccessResponse
from src.shared.utils.pagination import PaginationParams

router = APIRouter(prefix="/readings", tags=["Lecturas"])


def get_reading_service(
    reading_repo: IReadingRepository = Depends(lambda: SQLAlchemyReadingRepository()),
    device_repo: IDeviceRepository = Depends(lambda: SQLAlchemyDeviceRepository()),
) -> ReadingService:
    return ReadingService(reading_repo, device_repo)


# ── ESP32 write endpoints (X-API-Key) ─────────────────────────────────────────

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessResponse[ReadingResponse],
    summary="Ingresar lectura de sensores",
    description="El ESP32 envía una lectura usando su `X-API-Key`. Todos los campos de sensor son opcionales.",
    responses={
        201: {"description": "Lectura almacenada"},
        401: {"description": "API Key ausente o inválida"},
    },
)
async def ingest_reading(
    body: CreateReadingRequest,
    session: AsyncSession = Depends(get_db),
    device: Device = Depends(get_device_by_api_key),
    service: ReadingService = Depends(get_reading_service),
) -> SuccessResponse[ReadingResponse]:
    reading = await service.ingest(session, device=device, data=body)
    return SuccessResponse(
        data=ReadingResponse.model_validate(reading),
        message="Lectura almacenada correctamente.",
    )


@router.post(
    "/batch",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessResponse[dict],
    summary="Ingresar lote de lecturas (idempotente)",
    description=(
        "El ESP32 envía múltiples lecturas en un solo request. "
        "Si el `batch_id` ya existe, el lote se ignora (idempotente para reintentos)."
    ),
    responses={
        201: {"description": "Lote almacenado o ignorado (ya existía)"},
        401: {"description": "API Key ausente o inválida"},
    },
)
async def ingest_batch(
    body: BatchReadingRequest,
    session: AsyncSession = Depends(get_db),
    device: Device = Depends(get_device_by_api_key),
    service: ReadingService = Depends(get_reading_service),
) -> SuccessResponse[dict]:
    readings, already_existed = await service.ingest_batch(session, device=device, data=body)
    if already_existed:
        return SuccessResponse(
            data={"batch_id": body.batch_id, "inserted": 0, "skipped": True},
            message="Lote ya procesado anteriormente (idempotente).",
        )
    return SuccessResponse(
        data={"batch_id": body.batch_id, "inserted": len(readings), "skipped": False},
        message=f"Lote almacenado: {len(readings)} lectura(s).",
    )


# ── Dashboard read endpoints (JWT) ────────────────────────────────────────────

@router.get(
    "/latest",
    response_model=SuccessResponse[list[ReadingResponse]],
    summary="Última lectura por dispositivo",
    description="Devuelve la lectura más reciente de cada dispositivo activo del usuario.",
)
async def get_latest(
    session: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    service: ReadingService = Depends(get_reading_service),
) -> SuccessResponse[list[ReadingResponse]]:
    readings = await service.get_latest_per_device(session, propietario_id=user_id)
    return SuccessResponse(
        data=[ReadingResponse.model_validate(r) for r in readings],
        message="Últimas lecturas por dispositivo.",
    )


@router.get(
    "/aggregate",
    response_model=SuccessResponse[AggregateResponse],
    summary="Estadísticas agregadas",
    description=(
        "Calcula avg/min/max de un campo de sensor en un rango de tiempo. "
        "Campos válidos: `soil_humidity`, `temperature`, `air_humidity`, "
        "`pressure`, `altitude`, `light_lux`, `water_level`."
    ),
)
async def get_aggregate(
    field: str = Query(..., description="Campo del sensor a agregar"),
    device_id: int | None = Query(None, description="Filtrar por dispositivo"),
    start_date: datetime | None = Query(None, description="Desde (ISO 8601)"),
    end_date: datetime | None = Query(None, description="Hasta (ISO 8601)"),
    session: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    service: ReadingService = Depends(get_reading_service),
) -> SuccessResponse[AggregateResponse]:
    result = await service.aggregate(
        session,
        propietario_id=user_id,
        field=field,
        device_id=device_id,
        start_date=start_date,
        end_date=end_date,
    )
    return SuccessResponse(data=result, message="Estadísticas calculadas.")


@router.get(
    "/{reading_id}",
    response_model=SuccessResponse[ReadingResponse],
    summary="Obtener lectura por ID",
)
async def get_reading(
    reading_id: int,
    session: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    service: ReadingService = Depends(get_reading_service),
) -> SuccessResponse[ReadingResponse]:
    reading = await service.get_by_id(session, reading_id, propietario_id=user_id)
    return SuccessResponse(
        data=ReadingResponse.model_validate(reading),
        message="Lectura encontrada.",
    )


@router.get(
    "",
    response_model=PaginatedResponse[ReadingResponse],
    summary="Listar lecturas",
    description="Devuelve lecturas paginadas de los dispositivos del usuario, con filtros opcionales.",
)
async def list_readings(
    device_id: int | None = Query(None, description="Filtrar por dispositivo"),
    start_date: datetime | None = Query(None, description="Desde (ISO 8601)"),
    end_date: datetime | None = Query(None, description="Hasta (ISO 8601)"),
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    service: ReadingService = Depends(get_reading_service),
) -> PaginatedResponse[ReadingResponse]:
    readings, total = await service.list_readings(
        session,
        propietario_id=user_id,
        device_id=device_id,
        start_date=start_date,
        end_date=end_date,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    return PaginatedResponse(
        data=[ReadingResponse.model_validate(r) for r in readings],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            has_next=(pagination.offset + pagination.limit) < total,
        ),
    )
