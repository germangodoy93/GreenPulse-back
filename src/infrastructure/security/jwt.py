"""JWT access-token creation and validation.

Tokens are signed with HS256. The SECRET_KEY must be kept confidential;
rotating it invalidates all existing tokens.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from config.settings import get_settings

_settings = get_settings()

_ALGORITHM = _settings.JWT_ALGORITHM


def create_access_token(subject: str | int, extra_claims: dict[str, Any] | None = None) -> str:
    """Create a signed JWT access token.

    Args:
        subject: The token subject — typically the user's ID.
        extra_claims: Optional additional claims to embed (e.g. role).

    Returns:
        A signed JWT string.
    """
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(hours=_settings.JWT_EXPIRATION_HOURS),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, _settings.SECRET_KEY, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.

    Args:
        token: A JWT string from the Authorization header.

    Returns:
        The decoded payload dictionary.

    Raises:
        ValueError: If the token is invalid, expired, or tampered.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token, _settings.SECRET_KEY, algorithms=[_ALGORITHM]
        )
        return payload
    except JWTError as exc:
        raise ValueError(f"Token inválido o expirado: {exc}") from exc
