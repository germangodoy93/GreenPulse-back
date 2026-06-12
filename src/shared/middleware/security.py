"""Security-headers middleware.

Injects defensive HTTP headers on every response to mitigate common web
vulnerabilities: clickjacking, MIME sniffing, XSS via browsers, etc.

CSRF note: This API is stateless (JWT + API Key). It does not use cookie-based
sessions, so CSRF attacks are not applicable. Documented per OWASP API07.
"""

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# 1 year in seconds — HSTS max-age recommendation
_HSTS_MAX_AGE = 31_536_000


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add OWASP-recommended security headers to every HTTP response."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = (
            f"max-age={_HSTS_MAX_AGE}; includeSubDomains"
        )
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )
        return response
