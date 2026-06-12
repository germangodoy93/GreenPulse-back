"""Async SQLAlchemy engine factory.

The engine is created once at module import time.
SQLite (used in tests) requires a different pool configuration than PostgreSQL.
"""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool

from config.settings import get_settings

_settings = get_settings()


def _build_engine() -> AsyncEngine:
    """Create the async engine with driver-appropriate pool settings."""
    is_sqlite = _settings.DATABASE_URL.startswith("sqlite")

    common_kwargs: dict[str, object] = {
        "echo": _settings.DEBUG,
        "pool_pre_ping": not is_sqlite,
    }

    if is_sqlite:
        # StaticPool keeps one in-memory connection alive for the test session.
        # NullPool would close it between statements, losing the schema.
        return create_async_engine(
            _settings.DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            **common_kwargs,  # type: ignore[arg-type]
        )

    return create_async_engine(
        _settings.DATABASE_URL,
        pool_size=_settings.DATABASE_POOL_SIZE,
        max_overflow=_settings.DATABASE_MAX_OVERFLOW,
        **common_kwargs,  # type: ignore[arg-type]
    )


engine: AsyncEngine = _build_engine()


async def dispose_engine() -> None:
    """Gracefully dispose the connection pool on shutdown."""
    await engine.dispose()
