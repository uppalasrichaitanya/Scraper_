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
        "crawler.tasks.crawl_tasks",
        "crawler.tasks.search_tasks",
        "crawler.tasks.alert_tasks",
        "crawler.tasks.health_tasks",
        "crawler.tasks.lifecycle_tasks",
        "crawler.tasks.embedding_tasks",
        "crawler.tasks.resume_tasks",
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
        "crawl.run_adapter": {"queue": "crawl_playwright"},
        "search.index_single_job": {"queue": "crawl_default"},
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
    # Per-source health check every hour
    "adapter-health-check": {
        "task": "health_tasks.check_adapter_health",
        "schedule": 3600,
        "options": {"queue": "crawl_default"},
    },
    # Nightly bulk reindex from DB to Elasticsearch
    "reindex-elasticsearch": {
        "task": "jobs.reindex_elasticsearch",
        "schedule": crontab(minute=0, hour=2),  # 2 AM
        "args": [],
    },
    # Stale job lifecycle
    "stale-job-lifecycle": {
        "task": "lifecycle_tasks.mark_stale_jobs",
        "schedule": crontab(hour=20, minute=30),
        "options": {"queue": "crawl_default"},
    },
    # Daily alert dispatch
    "dispatch-daily-alerts": {
        "task": "alert_tasks.dispatch_alerts",
        "schedule": crontab(hour=2, minute=30),
        "args": ("daily",),
        "options": {"queue": "crawl_default"},
    },
    # Weekly alert dispatch
    "dispatch-weekly-alerts": {
        "task": "alert_tasks.dispatch_alerts",
        "schedule": crontab(hour=2, minute=30, day_of_week=1),
        "args": ("weekly",),
        "options": {"queue": "crawl_default"},
    },
    # Crawl Naukri every 4 hours
    "naukri-crawl": {
        "task": "crawl.run_adapter",
        "schedule": crontab(hour="*/4"),
        "args": ["naukri"],
    },
}
