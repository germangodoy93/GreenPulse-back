"""Application settings loaded from environment variables.

Uses Pydantic Settings for validation and type safety.
All sensitive values must be provided via .env file or environment variables.
"""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised, validated application configuration.

    Attributes defined here correspond 1-to-1 with variables in .env.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    APP_NAME: str = "GreenPulse API"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False

    # ── Server ────────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ── JWT / Security ────────────────────────────────────────────────────────
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    # ─────────────────────────────────────────────────────────────────────────
    @field_validator("DATABASE_URL")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        """Ensure the async asyncpg driver prefix is present for PostgreSQL."""
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        valid_prefixes = (
            "postgresql+asyncpg://",
            "sqlite+aiosqlite://",
        )
        if not any(v.startswith(p) for p in valid_prefixes):
            raise ValueError(
                "DATABASE_URL must start with 'postgresql+asyncpg://' "
                "or 'sqlite+aiosqlite://'."
            )
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_min_length(cls, v: str) -> str:
        """Reject obviously weak secret keys."""
        if len(v) < 32:  # noqa: PLR2004
            raise ValueError("SECRET_KEY must be at least 32 characters long.")
        return v


@lru_cache
def get_settings() -> Settings:
    """Return the cached singleton Settings instance.

    Using lru_cache ensures the .env file is read only once per process.
    In tests, clear the cache with get_settings.cache_clear() if needed.
    """
    return Settings()
