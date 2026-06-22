"""
Celery application factory.
All tasks are registered here via autodiscovery.
"""

from celery import Celery
from celery.schedules import crontab

from crawler.config import settings

app = Celery(
    "crawler",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "crawler.tasks.discover",
        "crawler.tasks.fetch_detail",
        "crawler.tasks.store",
        "crawler.tasks.cleanup",
        "crawler.tasks.health_check",
        "crawler.tasks.reindex",
    ],
)

# ── Celery configuration ──────────────────────────────────────────────────────
app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="Asia/Kolkata",
    enable_utc=True,
    # Task routing — two queues: default (httpx/scrapy) and playwright (browser)
    task_routes={
        "crawler.tasks.fetch_detail.fetch_playwright": {"queue": "crawl_playwright"},
        "crawler.tasks.fetch_detail.fetch_static": {"queue": "crawl_default"},
        "crawler.tasks.discover.*": {"queue": "crawl_default"},
        "crawler.tasks.store.*": {"queue": "crawl_default"},
        "jobs.cleanup_stale": {"queue": "crawl_default"},
        "crawl.health_check": {"queue": "crawl_default"},
        "jobs.reindex_elasticsearch": {"queue": "crawl_default"},
    },
    # Worker settings
    worker_prefetch_multiplier=1,       # prevent task hoarding in workers
    task_acks_late=True,                # only ack after task completes (prevents lost tasks on crash)
    task_reject_on_worker_lost=True,
    # Result expiry
    result_expires=3600,                # 1 hour
    # RedBeat scheduler (replaces default Beat — survives restarts)
    redbeat_redis_url=settings.REDIS_URL,
    beat_scheduler="redbeat.RedBeatScheduler",
)

# ── Periodic task schedule ────────────────────────────────────────────────────
app.conf.beat_schedule = {
    # Crawl all sources every 6 hours
    "discover-all-sources": {
        "task": "crawler.tasks.discover.discover_all",
        "schedule": crontab(minute=0, hour="*/6"),
        "args": [],
    },
    # Clean up stale jobs every 6 hours (offset 30min from discover)
    "cleanup-stale-jobs": {
        "task": "jobs.cleanup_stale",
        "schedule": crontab(minute=30, hour="*/6"),
        "args": [],
    },
    # Per-source health check every hour
    "health-check-all-sources": {
        "task": "crawl.health_check",
        "schedule": crontab(minute=0),   # every hour
        "args": [],
    },
    # Nightly bulk reindex from DB to Elasticsearch
    "reindex-elasticsearch": {
        "task": "jobs.reindex_elasticsearch",
        "schedule": crontab(minute=0, hour=2),  # 2 AM
        "args": [],
    },
}
