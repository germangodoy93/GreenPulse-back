"""Auth business logic.

All persistence goes through IUserRepository (never directly to the DB),
keeping this class database-agnostic and trivially unit-testable.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from src.infrastructure.security.hashing import hash_password, verify_password
from src.infrastructure.security.jwt import create_access_token
from src.modules.auth.models.user import User
from src.modules.auth.repositories.user_repository import IUserRepository
from src.shared.exceptions.domain import (
    ConflictException,
    NotFoundException,
    UnauthorizedException,
)

_settings = get_settings()


class AuthService:
    """Handles registration, login, and current-user resolution.

    Args:
        user_repo: A concrete IUserRepository implementation injected
                   by FastAPI's dependency system.
    """

    def __init__(self, user_repo: IUserRepository) -> None:
        self._repo = user_repo

    async def register(
        self,
        session: AsyncSession,
        *,
        email: str,
        password: str,
    ) -> User:
        """Register a new user account.

        Args:
            session: Active SQLAlchemy async session.
            email: Unique email address for the new account.
            password: Plain-text password (will be hashed before storage).

        Returns:
            The newly created User entity.

        Raises:
            ConflictException: If the email is already registered.
        """
        if await self._repo.exists_by_email(session, email):
            raise ConflictException(
                message="El email ya está registrado.",
                code="EMAIL_TAKEN",
                details={"email": email},
            )
        password_hash = hash_password(password)
        return await self._repo.create(
            session, email=email, password_hash=password_hash
        )

    async def login(
        self,
        session: AsyncSession,
        *,
        email: str,
        password: str,
    ) -> str:
        """Validate credentials and issue a JWT access token.

        Returns a generic error for wrong email OR wrong password
        to prevent user-enumeration attacks.

        Args:
            session: Active SQLAlchemy async session.
            email: Candidate email.
            password: Candidate plain-text password.

        Returns:
            A signed JWT string.

        Raises:
            UnauthorizedException: If credentials are invalid.
        """
        user = await self._repo.get_by_email(session, email)
        if user is None or not verify_password(password, user.password_hash):
            raise UnauthorizedException("Email o contraseña incorrectos.")

        return create_access_token(
            subject=user.id,
            extra_claims={"role": user.rol.value, "email": user.email},
        )

    async def get_by_id(self, session: AsyncSession, user_id: int) -> User:
        """Fetch an authenticated user by their ID.

        Args:
            session: Active SQLAlchemy async session.
            user_id: Primary key of the user to retrieve.

        Returns:
            The User entity.

        Raises:
            NotFoundException: If the user does not exist.
        """
        user = await self._repo.get_by_id(session, user_id)
        if user is None:
            raise NotFoundException("user", user_id)
        return user
