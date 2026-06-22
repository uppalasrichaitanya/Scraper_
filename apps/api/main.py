"""
Career Intelligence Platform — FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from core.config import settings
from core.database import engine
from core.logging import configure_logging
from middleware.logging import LoggingMiddleware
from middleware.request_id import RequestIDMiddleware

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup + shutdown hooks."""
    configure_logging()
    logger.info("Starting Career Intelligence Platform API", env=settings.ENVIRONMENT)

    # Verify DB connection on startup
    from core.database import check_db_connection
    await check_db_connection()

    # Verify Redis connection
    from core.redis import check_redis_connection
    await check_redis_connection()

    # Ensure Elasticsearch index exists
    from core.elasticsearch import get_es
    from search.setup import create_index_if_missing
    es = get_es()
    await create_index_if_missing(es, index_name="jobs")
    logger.info("Elasticsearch index 'jobs' ensured")

    logger.info("All connections healthy — API ready")

    yield

    logger.info("Shutting down API")
    from core.elasticsearch import close_es
    await close_es()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Career Intelligence Platform API",
        description="Job aggregation, search, and career intelligence platform",
        version="0.1.0",
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # ── Middleware (order matters — outermost first) ────────────────────────
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ────────────────────────────────────────────────────────────
    from routers.v1 import router as v1_router
    app.include_router(v1_router, prefix="/v1")

    # ── Health check (no auth, no versioning) ──────────────────────────────
    @app.get("/health", tags=["health"])
    async def health() -> dict:
        return {"status": "ok", "version": "0.1.0", "env": settings.ENVIRONMENT}

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
    )
