"""Unit tests for the password-strength validator."""

import pytest

from src.modules.auth.validators.password_validator import validate_password_strength


class TestPasswordStrength:
    def test_valid_password_passes(self) -> None:
        assert validate_password_strength("Segura1234") == "Segura1234"

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="8 caracteres"):
            validate_password_strength("Abc1")

    def test_no_uppercase_raises(self) -> None:
        with pytest.raises(ValueError, match="mayúscula"):
            validate_password_strength("segura1234")

    def test_no_lowercase_raises(self) -> None:
        with pytest.raises(ValueError, match="minúscula"):
            validate_password_strength("SEGURA1234")

    def test_no_digit_raises(self) -> None:
        with pytest.raises(ValueError, match="número"):
            validate_password_strength("SeguraABCD")

    def test_exactly_eight_chars_passes(self) -> None:
        assert validate_password_strength("Secure1a") == "Secure1a"
