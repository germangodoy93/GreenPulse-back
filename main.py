"""GreenPulse API — application entry point.

Assembles the FastAPI application: middleware stack, exception handlers,
versioned routers, and lifespan hooks for startup/shutdown.

Run locally:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from config.settings import get_settings
from src.infrastructure.database.connection import dispose_engine
from src.infrastructure.logging.config import setup_logging
from src.modules.auth.controllers.auth_controller import router as auth_router
from src.modules.system.controllers.health_controller import router as health_router
from src.shared.exceptions.domain import GreenPulseException
from src.shared.exceptions.handlers import (
    domain_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from src.shared.limiter import limiter
from src.shared.middleware.request_logging import RequestLoggingMiddleware
from src.shared.middleware.security import SecurityHeadersMiddleware

# ── Bootstrap ─────────────────────────────────────────────────────────────────
setup_logging()
_settings = get_settings()


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and graceful shutdown."""
    logger.info(
        "GreenPulse API starting",
        version=_settings.APP_VERSION,
        environment=_settings.ENVIRONMENT,
    )
    yield
    await dispose_engine()
    logger.info("GreenPulse API stopped")


# ── Application factory ───────────────────────────────────────────────────────
app = FastAPI(
    title=_settings.APP_NAME,
    version=_settings.APP_VERSION,
    description=(
        "API REST para el **Sistema Inteligente de Monitoreo Ambiental IoT** (GreenPulse). "
        "Recibe telemetría de nodos ESP32, persiste las lecturas, evalúa umbrales "
        "y expone alertas a un dashboard React.\n\n"
        "**Autenticación dispositivos:** header `X-API-Key`  \n"
        "**Autenticación usuarios:** `Authorization: Bearer <token>`"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

# ── Rate limiting ──────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(SlowAPIMiddleware)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

# ── Custom middleware ──────────────────────────────────────────────────────────
# Order matters: added last → executed first on request, last on response.
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# ── Exception handlers ────────────────────────────────────────────────────────
app.add_exception_handler(GreenPulseException, domain_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, unhandled_exception_handler)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")

# Stages 3-6 routers are registered here as modules are implemented:
# from src.modules.devices.controllers.device_controller import router as device_router
# app.include_router(device_router, prefix="/api/v1")
# …
