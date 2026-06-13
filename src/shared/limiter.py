"""Shared slowapi rate-limiter instance.

Centralising the Limiter here avoids circular imports when controllers
need to apply per-route limits stricter than the global default.

Usage in a controller:
    from src.shared.limiter import limiter

    @router.post("/login")
    @limiter.limit("5/minute")
    async def login(request: Request, ...) -> ...:
        ...
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from config.settings import get_settings

_settings = get_settings()

limiter: Limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{_settings.RATE_LIMIT_PER_MINUTE}/minute"],
)
