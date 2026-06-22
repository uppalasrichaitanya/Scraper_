"""
Redis connection pool using redis-py async client.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

import structlog
from fastapi import Depends
from redis.asyncio import Redis, ConnectionPool

from core.config import settings

logger = structlog.get_logger(__name__)

# ── Connection pool (singleton) ───────────────────────────────────────────────
_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_POOL_SIZE,
            decode_responses=True,
        )
    return _pool


def get_redis_client() -> Redis:
    """Return a Redis client backed by the shared connection pool."""
    return Redis(connection_pool=get_pool())


# ── FastAPI dependency ────────────────────────────────────────────────────────
async def get_redis() -> AsyncGenerator[Redis, None]:
    """FastAPI dependency providing a Redis client."""
    client = get_redis_client()
    try:
        yield client
    finally:
        await client.aclose()


# Type alias for route handlers
RedisClient = Annotated[Redis, Depends(get_redis)]


# ── Health check ──────────────────────────────────────────────────────────────
async def check_redis_connection() -> None:
    """Verify Redis is reachable. Called on application startup."""
    try:
        client = get_redis_client()
        await client.ping()
        await client.aclose()
        logger.info("Redis connection OK", url=settings.REDIS_URL)
    except Exception as e:
        logger.error("Redis connection FAILED", error=str(e))
        raise
