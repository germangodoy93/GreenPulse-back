"""Structured request/response logging middleware.

Logs every HTTP request with: timestamp, method, path, status code, latency,
and client IP. Sensitive paths (auth endpoints) are tagged but body content
is never logged.
"""

import time
from collections.abc import Awaitable, Callable

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Paths whose request/response bodies contain credentials — never log body.
_SENSITIVE_PATHS: frozenset[str] = frozenset(
    {"/api/v1/auth/login", "/api/v1/auth/register"}
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log each request cycle without exposing sensitive data."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            is_sensitive = request.url.path in _SENSITIVE_PATHS
            logger.info(
                "http_request",
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=duration_ms,
                client_ip=request.client.host if request.client else "unknown",
                sensitive=is_sensitive,
            )
