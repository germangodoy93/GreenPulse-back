"""Standardised API response envelopes.

Every endpoint returns one of these shapes so that clients can always rely
on a consistent top-level structure regardless of the endpoint.

Success:
    {"success": true, "data": {...}, "message": "...", "timestamp": "..."}

Error:
    {"success": false, "error": {"code": "...", "message": "...", "details": {...}}, "timestamp": "..."}

Paginated:
    {"success": true, "data": [...], "meta": {...}, "message": "...", "timestamp": "..."}
"""

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


def _utc_now() -> datetime:
    return datetime.now(UTC)


class SuccessResponse(BaseModel, Generic[DataT]):
    """Wrapper for single-resource or action responses."""

    success: bool = True
    data: DataT
    message: str
    timestamp: datetime = Field(default_factory=_utc_now)


class ErrorDetail(BaseModel):
    """Structured error payload embedded in ErrorResponse."""

    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Wrapper for all error responses."""

    success: bool = False
    error: ErrorDetail
    timestamp: datetime = Field(default_factory=_utc_now)


class PaginationMeta(BaseModel):
    """Pagination metadata attached to paginated list responses."""

    total: int = Field(..., description="Total de elementos en la colección")
    page: int = Field(..., description="Página actual (empieza en 1)")
    page_size: int = Field(..., description="Elementos por página")
    has_next: bool = Field(..., description="Indica si existe una página siguiente")


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Wrapper for paginated list responses."""

    success: bool = True
    data: list[DataT]
    meta: PaginationMeta
    message: str = "Consulta exitosa"
    timestamp: datetime = Field(default_factory=_utc_now)
