"""Reusable FastAPI security dependencies.

get_current_user_id  — decodes the JWT and returns the subject (user id).
                       Use this in any module that needs the authenticated
                       user's id without a DB query.

get_current_user     — convenience wrapper that also fetches the User row.
                       Import this in route handlers that need the full entity.
"""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.infrastructure.security.jwt import decode_access_token
from src.shared.exceptions.domain import UnauthorizedException

# auto_error=False: lets us raise our own UnauthorizedException instead of
# FastAPI's default HTTPException(401), keeping response format consistent.
_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> int:
    """Extract and validate the Bearer token; return the user's primary key.

    Args:
        credentials: Injected by FastAPI from the Authorization header.

    Returns:
        The authenticated user's integer id.

    Raises:
        UnauthorizedException: If the header is missing or the token is invalid.
    """
    if credentials is None:
        raise UnauthorizedException("Se requiere un token de autenticación Bearer.")
    try:
        payload = decode_access_token(credentials.credentials)
        return int(payload["sub"])
    except (ValueError, KeyError) as exc:
        raise UnauthorizedException("Token inválido o expirado.") from exc
