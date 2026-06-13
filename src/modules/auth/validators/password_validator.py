"""Password-strength validation rules.

Centralised here so the same rules apply everywhere a password is set
(registration, future password-change endpoint, CLI tools, etc.).
"""

import re

_MIN_LENGTH: int = 8


def validate_password_strength(password: str) -> str:
    """Enforce minimum password security requirements.

    Rules:
    - At least 8 characters
    - At least one uppercase letter (A-Z)
    - At least one lowercase letter (a-z)
    - At least one digit (0-9)

    Args:
        password: Plain-text candidate password.

    Returns:
        The validated password unchanged.

    Raises:
        ValueError: If any rule is violated (message is in Spanish for the API client).
    """
    if len(password) < _MIN_LENGTH:
        raise ValueError(
            f"La contraseña debe tener al menos {_MIN_LENGTH} caracteres."
        )
    if not re.search(r"[A-Z]", password):
        raise ValueError("La contraseña debe contener al menos una letra mayúscula.")
    if not re.search(r"[a-z]", password):
        raise ValueError("La contraseña debe contener al menos una letra minúscula.")
    if not re.search(r"\d", password):
        raise ValueError("La contraseña debe contener al menos un número.")
    return password
