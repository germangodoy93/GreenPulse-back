"""System health-check endpoint.

Used by cloud orchestrators (Railway, Render, Kubernetes) to determine
whether the service is alive. Returns 200 when the application is running;
does NOT check database connectivity (that is done via a separate readiness
probe, added in a future sprint).
"""

from fastapi import APIRouter

from config.settings import get_settings
from src.shared.response.schemas import SuccessResponse

router = APIRouter(tags=["Sistema"])

_settings = get_settings()


@router.get(
    "/health",
    response_model=SuccessResponse[dict[str, str]],
    summary="Healthcheck del servicio",
    description=(
        "Devuelve el estado operativo del servicio. "
        "Utilizado por los orquestadores cloud para determinar disponibilidad."
    ),
    responses={
        200: {
            "description": "Servicio operativo",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "status": "healthy",
                            "version": "0.1.0",
                            "environment": "development",
                        },
                        "message": "El servicio está operativo",
                        "timestamp": "2026-06-12T15:30:00Z",
                    }
                }
            },
        }
    },
)
async def health_check() -> SuccessResponse[dict[str, str]]:
    """Return the current liveness status of the API."""
    return SuccessResponse(
        data={
            "status": "healthy",
            "version": _settings.APP_VERSION,
            "environment": _settings.ENVIRONMENT,
        },
        message="El servicio está operativo",
    )
