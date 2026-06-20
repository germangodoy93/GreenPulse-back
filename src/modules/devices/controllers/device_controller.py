"""Devices HTTP controller — CRUD de nodos ESP32 y rotación de API Key."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.session import get_db
from src.infrastructure.security.dependencies import get_current_user_id
from src.modules.devices.dtos.device_dtos import (
    CreateDeviceRequest,
    DeviceCreatedResponse,
    DeviceResponse,
    UpdateDeviceRequest,
)
from src.modules.devices.repositories.device_repository import (
    IDeviceRepository,
    SQLAlchemyDeviceRepository,
)
from src.modules.devices.services.device_service import DeviceService
from src.shared.response.schemas import PaginatedResponse, PaginationMeta, SuccessResponse
from src.shared.utils.pagination import PaginationParams

router = APIRouter(prefix="/devices", tags=["Dispositivos"])


def get_device_repository() -> IDeviceRepository:
    return SQLAlchemyDeviceRepository()


def get_device_service(
    repo: IDeviceRepository = Depends(get_device_repository),
) -> DeviceService:
    return DeviceService(repo)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessResponse[DeviceCreatedResponse],
    summary="Registrar dispositivo ESP32",
    description=(
        "Crea un nuevo nodo sensor. "
        "La **API Key** se devuelve una sola vez — guárdala para configurar el ESP32."
    ),
    responses={
        201: {"description": "Dispositivo registrado, API Key incluida"},
        401: {"description": "Token JWT ausente o inválido"},
    },
)
async def register_device(
    body: CreateDeviceRequest,
    session: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    service: DeviceService = Depends(get_device_service),
) -> SuccessResponse[DeviceCreatedResponse]:
    device, plain_key = await service.create(session, data=body, propietario_id=user_id)
    return SuccessResponse(
        data=DeviceCreatedResponse(
            **DeviceResponse.model_validate(device).model_dump(),
            api_key=plain_key,
        ),
        message="Dispositivo registrado. Guarda la API Key, no se mostrará de nuevo.",
    )


@router.get(
    "",
    response_model=PaginatedResponse[DeviceResponse],
    summary="Listar dispositivos",
    description="Devuelve los dispositivos activos del usuario autenticado (paginado).",
    responses={
        200: {"description": "Lista de dispositivos"},
        401: {"description": "Token JWT ausente o inválido"},
    },
)
async def list_devices(
    pagination: PaginationParams = Depends(),
    session: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    service: DeviceService = Depends(get_device_service),
) -> PaginatedResponse[DeviceResponse]:
    devices, total = await service.list_by_owner(
        session,
        propietario_id=user_id,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    return PaginatedResponse(
        data=[DeviceResponse.model_validate(d) for d in devices],
        meta=PaginationMeta(
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            has_next=(pagination.offset + pagination.limit) < total,
        ),
    )


@router.get(
    "/{device_id}",
    response_model=SuccessResponse[DeviceResponse],
    summary="Obtener dispositivo",
    responses={
        200: {"description": "Detalle del dispositivo"},
        401: {"description": "Token JWT ausente o inválido"},
        403: {"description": "El dispositivo no pertenece al usuario"},
        404: {"description": "Dispositivo no encontrado"},
    },
)
async def get_device(
    device_id: int,
    session: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    service: DeviceService = Depends(get_device_service),
) -> SuccessResponse[DeviceResponse]:
    device = await service.get_by_id(session, device_id, propietario_id=user_id)
    return SuccessResponse(
        data=DeviceResponse.model_validate(device),
        message="Dispositivo encontrado.",
    )


@router.put(
    "/{device_id}",
    response_model=SuccessResponse[DeviceResponse],
    summary="Actualizar dispositivo",
    responses={
        200: {"description": "Dispositivo actualizado"},
        401: {"description": "Token JWT ausente o inválido"},
        403: {"description": "El dispositivo no pertenece al usuario"},
        404: {"description": "Dispositivo no encontrado"},
    },
)
async def update_device(
    device_id: int,
    body: UpdateDeviceRequest,
    session: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    service: DeviceService = Depends(get_device_service),
) -> SuccessResponse[DeviceResponse]:
    device = await service.update(session, device_id, data=body, propietario_id=user_id)
    return SuccessResponse(
        data=DeviceResponse.model_validate(device),
        message="Dispositivo actualizado.",
    )


@router.delete(
    "/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar dispositivo (soft delete)",
    responses={
        204: {"description": "Dispositivo desactivado"},
        401: {"description": "Token JWT ausente o inválido"},
        403: {"description": "El dispositivo no pertenece al usuario"},
        404: {"description": "Dispositivo no encontrado"},
    },
)
async def delete_device(
    device_id: int,
    session: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    service: DeviceService = Depends(get_device_service),
) -> None:
    await service.delete(session, device_id, propietario_id=user_id)


@router.post(
    "/{device_id}/rotate-key",
    response_model=SuccessResponse[DeviceCreatedResponse],
    summary="Rotar API Key",
    description=(
        "Genera una nueva API Key para el dispositivo, invalidando la anterior. "
        "La nueva clave se muestra **una sola vez**."
    ),
    responses={
        200: {"description": "Nueva API Key generada"},
        401: {"description": "Token JWT ausente o inválido"},
        403: {"description": "El dispositivo no pertenece al usuario"},
        404: {"description": "Dispositivo no encontrado"},
    },
)
async def rotate_api_key(
    device_id: int,
    session: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    service: DeviceService = Depends(get_device_service),
) -> SuccessResponse[DeviceCreatedResponse]:
    device, plain_key = await service.rotate_key(session, device_id, propietario_id=user_id)
    return SuccessResponse(
        data=DeviceCreatedResponse(
            **DeviceResponse.model_validate(device).model_dump(),
            api_key=plain_key,
        ),
        message="API Key regenerada. Guarda la nueva clave, no se mostrará de nuevo.",
    )
