"""Auth HTTP controller — registers, login y perfil del usuario.

Rate limiting:
  - POST /login: 5 intentos/minuto por IP (protección brute-force).
  - POST /register: 10/minuto (previene spam de cuentas).

CSRF: no aplica — API stateless con JWT (OWASP API07).
"""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from src.infrastructure.database.session import get_db
from src.infrastructure.security.dependencies import get_current_user_id
from src.modules.auth.dtos.auth_dtos import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from src.modules.auth.repositories.user_repository import (
    IUserRepository,
    SQLAlchemyUserRepository,
)
from src.modules.auth.services.auth_service import AuthService
from src.shared.limiter import limiter
from src.shared.response.schemas import SuccessResponse

router = APIRouter(prefix="/auth", tags=["Autenticación"])
_settings = get_settings()


# ── Dependency factories ───────────────────────────────────────────────────────

def get_user_repository() -> IUserRepository:
    """Provide the concrete user repository (overridable in tests)."""
    return SQLAlchemyUserRepository()


def get_auth_service(
    repo: IUserRepository = Depends(get_user_repository),
) -> AuthService:
    """Provide the AuthService with injected repository (DIP)."""
    return AuthService(user_repo=repo)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=SuccessResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario",
    description="Crea una cuenta de usuario. El email debe ser único.",
    responses={
        201: {"description": "Usuario creado correctamente"},
        409: {"description": "El email ya está registrado"},
        422: {"description": "Datos de entrada inválidos"},
        429: {"description": "Demasiados intentos — espera un minuto"},
    },
)
@limiter.limit("10/minute")
async def register(
    request: Request,  # required by slowapi
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(get_auth_service),
) -> SuccessResponse[UserResponse]:
    """Create a new user account and return the public user profile."""
    user = await service.register(db, email=body.email, password=body.password)
    return SuccessResponse(
        data=UserResponse.model_validate(user),
        message="Usuario registrado correctamente.",
    )


@router.post(
    "/login",
    response_model=SuccessResponse[TokenResponse],
    summary="Iniciar sesión",
    description=(
        "Valida las credenciales y devuelve un JWT Bearer token. "
        "Limitado a **5 intentos por minuto** por IP."
    ),
    responses={
        200: {"description": "Login exitoso, token devuelto"},
        401: {"description": "Email o contraseña incorrectos"},
        429: {"description": "Demasiados intentos — espera un minuto"},
    },
)
@limiter.limit("5/minute")
async def login(
    request: Request,  # required by slowapi
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(get_auth_service),
) -> SuccessResponse[TokenResponse]:
    """Validate credentials and issue a JWT access token."""
    token = await service.login(db, email=body.email, password=body.password)
    expires_in = _settings.JWT_EXPIRATION_HOURS * 3600
    return SuccessResponse(
        data=TokenResponse(
            access_token=token,
            expires_in=expires_in,
        ),
        message="Login exitoso.",
    )


@router.get(
    "/me",
    response_model=SuccessResponse[UserResponse],
    summary="Perfil del usuario autenticado",
    description="Devuelve los datos del usuario identificado por el JWT Bearer token.",
    responses={
        200: {"description": "Datos del usuario autenticado"},
        401: {"description": "Token ausente, inválido o expirado"},
    },
)
async def get_me(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(get_auth_service),
) -> SuccessResponse[UserResponse]:
    """Return the authenticated user's profile."""
    user = await service.get_by_id(db, user_id)
    return SuccessResponse(
        data=UserResponse.model_validate(user),
        message="Datos del usuario autenticado.",
    )
