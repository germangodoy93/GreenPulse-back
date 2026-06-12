"""Reusable pagination dependency for FastAPI endpoints.

Usage:
    @router.get("/items")
    async def list_items(
        pagination: PaginationParams = Depends(),
        db: AsyncSession = Depends(get_db),
    ) -> PaginatedResponse[ItemResponse]:
        items = await service.list(db, offset=pagination.offset, limit=pagination.limit)
        ...
"""

from dataclasses import dataclass

from fastapi import Query

DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100


@dataclass
class PaginationParams:
    """Query-parameter based pagination extracted via FastAPI dependency injection.

    Args:
        page: 1-based page number.
        page_size: Number of items per page (max 100).
    """

    page: int = Query(default=1, ge=1, description="Número de página (empieza en 1)")
    page_size: int = Query(
        default=DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        alias="page_size",
        description=f"Elementos por página (máximo {MAX_PAGE_SIZE})",
    )

    @property
    def offset(self) -> int:
        """SQL OFFSET derived from page and page_size."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """SQL LIMIT — alias for page_size for clarity at call sites."""
        return self.page_size
