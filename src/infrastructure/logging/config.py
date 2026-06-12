"""Loguru logging configuration.

- Development: human-readable coloured output.
- Production / staging: single-line JSON for log aggregators (Loki, Datadog…).

Sensitive fields (passwords, tokens, API keys) must NEVER appear in log messages.
"""

import sys
from typing import TYPE_CHECKING

from loguru import logger

from config.settings import get_settings

if TYPE_CHECKING:
    from loguru import Record

_DEV_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
    "<level>{message}</level>"
)


def _json_sink_filter(record: "Record") -> bool:
    """Exclude DEBUG records in non-debug production logs."""
    settings = get_settings()
    if settings.ENVIRONMENT == "production" and not settings.DEBUG:
        return record["level"].no >= 20  # INFO and above  # noqa: PLR2004
    return True


def setup_logging() -> None:
    """Configure loguru based on the current environment.

    Call this once at application startup before the first log statement.
    """
    settings = get_settings()
    logger.remove()  # Remove the default stderr handler

    if settings.ENVIRONMENT in {"staging", "production"}:
        logger.add(
            sys.stdout,
            level="INFO",
            serialize=True,  # Outputs JSON
            filter=_json_sink_filter,
            enqueue=True,  # Thread-safe async logging
        )
    else:
        logger.add(
            sys.stdout,
            level="DEBUG" if settings.DEBUG else "INFO",
            format=_DEV_FORMAT,
            colorize=True,
        )

    logger.info(
        "Logging initialised",
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
    )
