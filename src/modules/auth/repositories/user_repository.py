"""User repository: abstract interface + SQLAlchemy implementation.

Following ISP and DIP: services depend on IUserRepository (the abstraction),
never on SQLAlchemyUserRepository (the implementation).
This allows swapping the DB layer in tests without touching business logic.
"""

from abc import ABC, abstractmethod

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.auth.models.user import User, UserRole


class IUserRepository(ABC):
    """Abstract contract for user persistence operations."""

    @abstractmethod
    async def create(
        self,
        session: AsyncSession,
        *,
        email: str,
        password_hash: str,
        rol: UserRole = UserRole.viewer,
    ) -> User:
        """Persist a new user and return the hydrated entity."""

    @abstractmethod
    async def get_by_id(self, session: AsyncSession, user_id: int) -> User | None:
        """Return the user with the given primary key, or None."""

    @abstractmethod
    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        """Return the user with the given email address, or None."""

    @abstractmethod
    async def exists_by_email(self, session: AsyncSession, email: str) -> bool:
        """Return True if an account with *email* already exists."""


class SQLAlchemyUserRepository(IUserRepository):
    """Concrete user repository backed by SQLAlchemy async ORM.

    Uses parameterised queries exclusively — no string concatenation —
    to prevent SQL injection (OWASP A03:2021).
    """

    async def create(
        self,
        session: AsyncSession,
        *,
        email: str,
        password_hash: str,
        rol: UserRole = UserRole.viewer,
    ) -> User:
        """Insert a new user row and return it with its generated id."""
        user = User(email=email, password_hash=password_hash, rol=rol)
        session.add(user)
        await session.flush()      # Flush to get DB-generated id
        await session.refresh(user)
        return user

    async def get_by_id(self, session: AsyncSession, user_id: int) -> User | None:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def exists_by_email(self, session: AsyncSession, email: str) -> bool:
        result = await session.execute(
            select(exists().where(User.email == email))
        )
        return bool(result.scalar())
