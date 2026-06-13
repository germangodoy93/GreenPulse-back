"""Unit tests for AuthService.

All repository calls are mocked — no database connection required.
Tests verify business rules: duplicate-email rejection, credential validation,
token issuance, and user retrieval.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.security.hashing import hash_password
from src.modules.auth.models.user import User, UserRole
from src.modules.auth.services.auth_service import AuthService
from src.shared.exceptions.domain import (
    ConflictException,
    NotFoundException,
    UnauthorizedException,
)


def _make_user(
    user_id: int = 1,
    email: str = "test@greenpulse.io",
    password: str = "Segura1234",
    rol: UserRole = UserRole.viewer,
) -> User:
    """Build a User instance without hitting the database."""
    user = MagicMock(spec=User)
    user.id = user_id
    user.email = email
    user.password_hash = hash_password(password)
    user.rol = rol
    return user


@pytest.fixture
def mock_repo() -> AsyncMock:
    return AsyncMock()  # spec not needed; method calls are verified by name


@pytest.fixture
def service(mock_repo: AsyncMock) -> AuthService:
    return AuthService(user_repo=mock_repo)


@pytest.fixture
def mock_session() -> AsyncMock:
    return AsyncMock()


# ── register ──────────────────────────────────────────────────────────────────

class TestRegister:
    async def test_creates_user_when_email_is_new(
        self, service: AuthService, mock_repo: AsyncMock, mock_session: AsyncMock
    ) -> None:
        mock_repo.exists_by_email.return_value = False
        mock_repo.create.return_value = _make_user()

        user = await service.register(mock_session, email="new@test.io", password="Segura1234")

        assert user.email == "test@greenpulse.io"
        mock_repo.create.assert_called_once()

    async def test_raises_conflict_when_email_taken(
        self, service: AuthService, mock_repo: AsyncMock, mock_session: AsyncMock
    ) -> None:
        mock_repo.exists_by_email.return_value = True

        with pytest.raises(ConflictException) as exc_info:
            await service.register(mock_session, email="dup@test.io", password="Segura1234")

        assert exc_info.value.code == "EMAIL_TAKEN"
        mock_repo.create.assert_not_called()

    async def test_password_is_hashed_before_storage(
        self, service: AuthService, mock_repo: AsyncMock, mock_session: AsyncMock
    ) -> None:
        mock_repo.exists_by_email.return_value = False
        mock_repo.create.return_value = _make_user()

        await service.register(mock_session, email="u@t.io", password="Segura1234")

        call_kwargs = mock_repo.create.call_args.kwargs
        assert call_kwargs["password_hash"] != "Segura1234"
        assert call_kwargs["password_hash"].startswith("$2b$")


# ── login ─────────────────────────────────────────────────────────────────────

class TestLogin:
    async def test_returns_token_with_correct_credentials(
        self, service: AuthService, mock_repo: AsyncMock, mock_session: AsyncMock
    ) -> None:
        mock_repo.get_by_email.return_value = _make_user(password="Segura1234")

        token = await service.login(mock_session, email="t@t.io", password="Segura1234")

        assert isinstance(token, str)
        assert len(token) > 20  # noqa: PLR2004

    async def test_raises_unauthorized_with_wrong_password(
        self, service: AuthService, mock_repo: AsyncMock, mock_session: AsyncMock
    ) -> None:
        mock_repo.get_by_email.return_value = _make_user(password="Correcta1")

        with pytest.raises(UnauthorizedException):
            await service.login(mock_session, email="t@t.io", password="Incorrecta1")

    async def test_raises_unauthorized_when_user_not_found(
        self, service: AuthService, mock_repo: AsyncMock, mock_session: AsyncMock
    ) -> None:
        mock_repo.get_by_email.return_value = None

        with pytest.raises(UnauthorizedException):
            await service.login(mock_session, email="ghost@t.io", password="Segura1234")

    async def test_generic_error_prevents_user_enumeration(
        self, service: AuthService, mock_repo: AsyncMock, mock_session: AsyncMock
    ) -> None:
        """Both 'user not found' and 'wrong password' must raise the same error."""
        mock_repo.get_by_email.return_value = None
        with pytest.raises(UnauthorizedException) as not_found:
            await service.login(mock_session, email="x@t.io", password="Segura1234")

        mock_repo.get_by_email.return_value = _make_user(password="Otra1234")
        with pytest.raises(UnauthorizedException) as wrong_pass:
            await service.login(mock_session, email="x@t.io", password="Segura1234")

        assert not_found.value.message == wrong_pass.value.message


# ── get_by_id ─────────────────────────────────────────────────────────────────

class TestGetById:
    async def test_returns_user_when_found(
        self, service: AuthService, mock_repo: AsyncMock, mock_session: AsyncMock
    ) -> None:
        expected = _make_user(user_id=42)
        mock_repo.get_by_id.return_value = expected

        result = await service.get_by_id(mock_session, 42)

        assert result.id == 42

    async def test_raises_not_found_when_missing(
        self, service: AuthService, mock_repo: AsyncMock, mock_session: AsyncMock
    ) -> None:
        mock_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundException):
            await service.get_by_id(mock_session, 999)
