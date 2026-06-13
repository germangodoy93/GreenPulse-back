"""Pydantic DTOs for the Auth module.

Separate Request and Response schemas prevent accidentally exposing
sensitive fields (e.g. password_hash) in API responses.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.modules.auth.models.user import UserRole
from src.modules.auth.validators.password_validator import validate_password_strength


# ── Request DTOs ──────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    """Payload for POST /auth/register."""

    email: EmailStr = Field(..., description="Dirección de correo electrónico única")
    password: str = Field(
        ...,
        min_length=8,
        description="Contraseña (mínimo 8 caracteres, mayúscula, minúscula y número)",
    )

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Apply domain password rules beyond Pydantic's min_length."""
        return validate_password_strength(v)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "operador@greenpulse.io",
                "password": "Segura1234",
            }
        }
    )


class LoginRequest(BaseModel):
    """Payload for POST /auth/login."""

    email: EmailStr = Field(..., description="Email registrado")
    password: str = Field(..., description="Contraseña en texto plano")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "operador@greenpulse.io",
                "password": "Segura1234",
            }
        }
    )


# ── Response DTOs ─────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    """Public representation of a user — never includes password_hash."""

    id: int
    email: EmailStr
    rol: UserRole
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "email": "operador@greenpulse.io",
                "rol": "viewer",
                "created_at": "2026-06-12T15:30:00Z",
            }
        },
    )


class TokenResponse(BaseModel):
    """JWT token issued after successful login."""

    access_token: str = Field(..., description="JWT Bearer token")
    token_type: str = Field(default="bearer", description="Tipo de token (siempre 'bearer')")
    expires_in: int = Field(..., description="Tiempo de expiración en segundos")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400,
            }
        }
    )
