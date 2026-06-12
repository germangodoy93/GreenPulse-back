"""Async database session factory and FastAPI dependency.

Usage in a route:
    async def my_endpoint(db: AsyncSession = Depends(get_db)) -> ...:
        ...
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.infrastructure.database.connection import engine

AsyncSessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession and handle commit/rollback automatically.

    This is the standard FastAPI dependency for database access.
    The session is committed on success and rolled back on any exception.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
