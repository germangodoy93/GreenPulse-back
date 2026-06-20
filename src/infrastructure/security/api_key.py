"""API key generation and verification for IoT device authentication.

Plain-text keys are shown to the user exactly once at device registration.
The SHA-256 hex digest is stored in the database (indexed for O(1) lookup).
SHA-256 is appropriate here because keys are random 32-byte secrets — unlike
user passwords, they are not susceptible to dictionary attacks.
"""

import hashlib
import hmac
import secrets

_KEY_BYTES = 32


def _hash_key(plain_key: str) -> str:
    return hashlib.sha256(plain_key.encode()).hexdigest()


def generate_api_key() -> tuple[str, str]:
    """Generate a new random API key and its SHA-256 digest.

    Returns:
        A tuple of (plain_key, hashed_key).
        Store *hashed_key* in the database; return *plain_key* to the client
        once and discard it — it cannot be recovered later.
    """
    plain_key = secrets.token_urlsafe(_KEY_BYTES)
    return plain_key, _hash_key(plain_key)


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verify a plain API key against its stored SHA-256 hash."""
    return hmac.compare_digest(_hash_key(plain_key), hashed_key)


def compute_api_key_hash(plain_key: str) -> str:
    """Compute the SHA-256 digest used for database lookups."""
    return _hash_key(plain_key)
