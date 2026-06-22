"""
Crawler service configuration via pydantic-settings.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class CrawlerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    LOG_LEVEL: str = "info"

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://jobs:devpassword@localhost:5432/jobsdb"

    # ── Redis / Celery ────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Crawler settings ──────────────────────────────────────────────────────
    # Default request delay range (seconds) — Gaussian random between min/max
    REQUEST_DELAY_MIN: float = 3.0
    REQUEST_DELAY_MAX: float = 8.0
    # High-protection domain delay
    REQUEST_DELAY_HP_MIN: float = 15.0
    REQUEST_DELAY_HP_MAX: float = 30.0

    # Browser context pool size (Playwright)
    BROWSER_POOL_SIZE: int = 3
    # Restart context every N requests (memory management)
    BROWSER_CONTEXT_MAX_REQUESTS: int = 50
    # Restart browser every N requests
    BROWSER_MAX_REQUESTS: int = 500

    # ── Health check alerting ─────────────────────────────────────────────────
    SLACK_WEBHOOK_URL: str = ""
    HEALTH_CHECK_WINDOW_MINUTES: int = 60
    HEALTH_ALERT_THRESHOLD: float = 0.85    # alert if success rate < 85%
    HEALTH_PAUSE_THRESHOLD: float = 0.70    # pause adapter if < 70%

    # ── Anti-detection (Phase 2) ──────────────────────────────────────────────
    CAPTCHA_API_KEY: str = ""
    PROXY_USERNAME: str = ""
    PROXY_PASSWORD: str = ""
    PROXY_HOST: str = ""

    # ── OpenAI (Phase 2) ──────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""


@lru_cache
def get_settings() -> CrawlerSettings:
    return CrawlerSettings()


settings = get_settings()
