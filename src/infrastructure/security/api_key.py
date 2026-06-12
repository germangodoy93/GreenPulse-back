"""API key generation and verification for IoT device authentication.

Plain-text keys are shown to the user exactly once at device registration.
Only the bcrypt hash is stored in the database to limit the blast radius
of a DB compromise.
"""

import secrets

from passlib.context import CryptContext

_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 32 URL-safe bytes → 43 characters, plenty of entropy.
_KEY_BYTES = 32


def generate_api_key() -> tuple[str, str]:
    """Generate a new random API key and its bcrypt hash.

    Returns:
        A tuple of (plain_key, hashed_key).
        Store *hashed_key* in the database; return *plain_key* to the client
        once and discard it — it cannot be recovered later.
    """
    plain_key = secrets.token_urlsafe(_KEY_BYTES)
    hashed_key = _CONTEXT.hash(plain_key)
    return plain_key, hashed_key


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verify a plain API key against its stored hash.

    Args:
        plain_key: The raw key from the X-API-Key request header.
        hashed_key: The bcrypt hash stored in the database.

    Returns:
        True if the key is valid, False otherwise.
    """
    return bool(_CONTEXT.verify(plain_key, hashed_key))
