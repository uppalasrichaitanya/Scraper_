"""
Structured access logging middleware.
Logs every request as a JSON object with: method, path, status, duration_ms, user_agent.
"""

import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        # Skip health check spam in logs
        if request.url.path == "/health":
            return response

        log_fn = logger.warning if response.status_code >= 400 else logger.info

        log_fn(
            "http_request",
            method=request.method,
            path=request.url.path,
            query=str(request.url.query) or None,
            status=response.status_code,
            duration_ms=duration_ms,
            user_agent=request.headers.get("User-Agent"),
            ip=request.client.host if request.client else None,
        )

        response.headers["X-Response-Time"] = f"{duration_ms}ms"
        return response
