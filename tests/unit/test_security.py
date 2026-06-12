"""Unit tests for infrastructure/security utilities.

All tests use mocks or pure functions — no database or network required.
"""

import pytest

from src.infrastructure.security.api_key import generate_api_key, verify_api_key
from src.infrastructure.security.hashing import hash_password, verify_password
from src.infrastructure.security.jwt import create_access_token, decode_access_token


class TestPasswordHashing:
    def test_hash_is_not_plain_text(self) -> None:
        hashed = hash_password("mysecretpassword")
        assert hashed != "mysecretpassword"

    def test_correct_password_verifies(self) -> None:
        hashed = hash_password("correct-horse-battery-staple")
        assert verify_password("correct-horse-battery-staple", hashed) is True

    def test_wrong_password_does_not_verify(self) -> None:
        hashed = hash_password("correct")
        assert verify_password("incorrect", hashed) is False

    def test_two_hashes_differ(self) -> None:
        """bcrypt uses a random salt — same input must not produce same hash."""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2


class TestJWT:
    def test_token_round_trip(self) -> None:
        token = create_access_token(subject=42)
        payload = decode_access_token(token)
        assert payload["sub"] == "42"

    def test_extra_claims_are_embedded(self) -> None:
        token = create_access_token(subject=1, extra_claims={"role": "admin"})
        payload = decode_access_token(token)
        assert payload["role"] == "admin"

    def test_tampered_token_raises(self) -> None:
        token = create_access_token(subject=1)
        tampered = token[:-4] + "xxxx"
        with pytest.raises(ValueError, match="Token inválido"):
            decode_access_token(tampered)


class TestApiKey:
    def test_generate_returns_tuple(self) -> None:
        plain, hashed = generate_api_key()
        assert plain != hashed

    def test_plain_key_length(self) -> None:
        plain, _ = generate_api_key()
        # secrets.token_urlsafe(32) → 43 URL-safe chars
        assert len(plain) >= 40  # noqa: PLR2004

    def test_correct_key_verifies(self) -> None:
        plain, hashed = generate_api_key()
        assert verify_api_key(plain, hashed) is True

    def test_wrong_key_does_not_verify(self) -> None:
        _, hashed = generate_api_key()
        assert verify_api_key("wrong-key", hashed) is False
