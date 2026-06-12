"""Domain exception hierarchy.

All application-specific exceptions extend GreenPulseException so that a
single FastAPI exception handler can convert them to consistent JSON responses.

Usage:
    raise DeviceNotFoundException(device_id=42)
    raise ConflictException("El email ya está registrado", code="EMAIL_TAKEN")
"""

from typing import Any


class GreenPulseException(Exception):
    """Base exception for all GreenPulse domain errors.

    Args:
        message: Human-readable message shown to the API client (in Spanish).
        code: Machine-readable uppercase error code, e.g. "DEVICE_NOT_FOUND".
        status_code: HTTP status code for the response.
        details: Optional dict with extra context (IDs, field names, etc.).
    """

    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class NotFoundException(GreenPulseException):
    """Raised when a requested resource does not exist (HTTP 404)."""

    def __init__(self, resource: str, resource_id: Any) -> None:
        super().__init__(
            message=f"El recurso '{resource}' no fue encontrado.",
            code=f"{resource.upper()}_NOT_FOUND",
            status_code=404,
            details={"id": resource_id},
        )


class ConflictException(GreenPulseException):
    """Raised on uniqueness violations or business-rule conflicts (HTTP 409)."""

    def __init__(
        self,
        message: str,
        code: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=409, details=details)


class UnauthorizedException(GreenPulseException):
    """Raised when authentication credentials are missing or invalid (HTTP 401)."""

    def __init__(self, message: str = "Credenciales de autenticación inválidas o ausentes.") -> None:
        super().__init__(message=message, code="UNAUTHORIZED", status_code=401)


class ForbiddenException(GreenPulseException):
    """Raised when the authenticated user lacks permission (HTTP 403)."""

    def __init__(self, message: str = "No tiene permisos para realizar esta acción.") -> None:
        super().__init__(message=message, code="FORBIDDEN", status_code=403)


class ValidationException(GreenPulseException):
    """Raised for domain-level validation failures (HTTP 422)."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        )
