"""Shared pytest fixtures for unit and integration tests.

The test database uses SQLite in-memory via aiosqlite so tests run without
a live PostgreSQL instance. The schema is rebuilt from scratch for every
test session.

Environment variables are set BEFORE importing application modules so that
get_settings() (which is lru_cached) picks up the test values.
"""

import os

# Override settings before any app import resolves them.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-32-chars-long!!")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "false")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool  # noqa: E402

from main import app  # noqa: E402
from src.infrastructure.database.base import Base  # noqa: E402
from src.infrastructure.database.session import get_db  # noqa: E402

_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
async def test_engine():  # type: ignore[return]
    """Create an in-memory SQLite engine and build the schema once per session."""
    engine = create_async_engine(
        _TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):  # type: ignore[return]
    """Provide a transactional session rolled back after each test."""
    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session: AsyncSession):  # type: ignore[return]
    """Async HTTP client backed by the test app with overridden DB session."""

    async def _override_get_db():  # type: ignore[return]
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
