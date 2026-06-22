"""
Rate limiting via slowapi (limits library).
- Unauthenticated: 100 req/min per IP
- Authenticated:   1000 req/min per user_id
- Auth endpoints:  10 req/15min per IP
"""

from fastapi import Request, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse


def _get_key(request: Request) -> str:
    """
    Rate limit key: use user_id if authenticated, else IP address.
    Authenticated users get a much higher limit (1000/min vs 100/min).
    """
    # JWT auth sets request.state.user_id in get_current_user dependency
    user_id: str | None = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    return get_remote_address(request)


limiter = Limiter(key_func=_get_key, default_limits=["100/minute"])


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Return 429 with Retry-After header."""
    retry_after = getattr(exc, "retry_after", 60)
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please slow down.",
            "retry_after_seconds": retry_after,
        },
        headers={"Retry-After": str(retry_after)},
    )
