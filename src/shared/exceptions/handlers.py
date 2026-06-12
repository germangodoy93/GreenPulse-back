"""FastAPI exception handlers for consistent JSON error responses.

Register these handlers in main.py so every unhandled exception returns
the standard ErrorResponse envelope instead of FastAPI's default detail format.
"""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger

from src.shared.exceptions.domain import GreenPulseException
from src.shared.response.schemas import ErrorDetail, ErrorResponse


async def domain_exception_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """Convert a GreenPulseException into the standard error envelope."""
    assert isinstance(exc, GreenPulseException)  # noqa: S101
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=ErrorDetail(
                code=exc.code,
                message=exc.message,
                details=exc.details,
            )
        ).model_dump(mode="json"),
    )


async def validation_exception_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """Convert Pydantic RequestValidationError into the standard error envelope."""
    assert isinstance(exc, RequestValidationError)  # noqa: S101
    field_errors = [
        {
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message="Los datos de la solicitud contienen errores de validación.",
                details={"errors": field_errors},
            )
        ).model_dump(mode="json"),
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Catch-all handler for unexpected server errors.

    Logs the full traceback but returns a generic message to avoid leaking
    internal details to the client.
    """
    logger.exception(
        "Unhandled exception",
        method=request.method,
        path=request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message="Error interno del servidor. Inténtalo de nuevo más tarde.",
            )
        ).model_dump(mode="json"),
    )
