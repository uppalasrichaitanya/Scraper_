"""
conftest.py — Testcontainers fixtures for integration tests.

Spins up real PostgreSQL and Redis containers per test session.
Runs all Alembic migrations so tests hit a schema-accurate DB.
Each test function gets a clean transaction that is rolled back.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

# ── Session-scoped containers ─────────────────────────────────────────────────

@pytest.fixture(scope="session")
def postgres_container():
    """Start a real PostgreSQL 16 container for the whole test session."""
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def redis_container():
    """Start a real Redis 7 container for the whole test session."""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis


@pytest.fixture(scope="session")
def db_url(postgres_container: PostgresContainer) -> str:
    """asyncpg URL for the test Postgres container."""
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    user = postgres_container.username
    pw = postgres_container.password
    db = postgres_container.dbname
    return f"postgresql+asyncpg://{user}:{pw}@{host}:{port}/{db}"


@pytest.fixture(scope="session")
def sync_db_url(postgres_container: PostgresContainer) -> str:
    """psycopg2 URL for Alembic migrations (sync)."""
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    user = postgres_container.username
    pw = postgres_container.password
    db = postgres_container.dbname
    return f"postgresql://{user}:{pw}@{host}:{port}/{db}"


@pytest.fixture(scope="session")
def redis_url(redis_container: RedisContainer) -> str:
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    return f"redis://{host}:{port}/0"


# ── Run Alembic migrations once per session ───────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def run_migrations(sync_db_url: str):
    """Run alembic upgrade head against the test container."""
    from alembic.config import Config
    from alembic import command
    from core.config import settings

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", sync_db_url)
    
    # Ensure alembic/env.py picks up the correct URL
    settings.DATABASE_SYNC_URL = sync_db_url
    
    command.upgrade(cfg, "head")


# ── Async engine + session factory ───────────────────────────────────────────

@pytest.fixture(scope="session")
def async_engine(db_url: str):
    engine = create_async_engine(db_url, echo=False)
    yield engine
    # Note: can't await in sync fixture — engine cleanup handled by GC


@pytest.fixture(scope="session")
def session_factory(async_engine):
    return async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def db(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Per-test async session that rolls back all changes after each test.
    Uses SAVEPOINT so nested transactions work correctly.
    """
    async with async_engine.connect() as conn:
        await conn.begin()
        await conn.begin_nested()
        
        async_session = async_sessionmaker(
            bind=conn,
            class_=AsyncSession,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint"
        )
        async with async_session() as session:
            yield session
            
        await conn.rollback()


# ── FastAPI test client ───────────────────────────────────────────────────────

@pytest.fixture
async def client(db_url: str, redis_url: str, db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTPX client pointed at the FastAPI app.
    Overrides DATABASE_URL and REDIS_URL with container values.
    """
    os.environ["DATABASE_URL"] = db_url
    os.environ["REDIS_URL"] = redis_url

    # Import app AFTER env override so Settings picks up test URLs
    from main import create_app
    from core.config import get_settings
    from core.database import get_db
    get_settings.cache_clear()  # type: ignore[attr-defined]

    app = create_app()
    
    async def override_get_db():
        yield db
        
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="https://test",
    ) as ac:
        yield ac
