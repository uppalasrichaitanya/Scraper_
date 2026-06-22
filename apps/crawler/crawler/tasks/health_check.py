"""
health_check.py — Per-source success rate monitor.

Queries CrawlRun records from the last hour and alerts if success rate drops
below thresholds. Wires to Slack/email in Phase E.
"""
import asyncio
import datetime
import logging

from ..celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="crawl.health_check")
def check_all_sources() -> None:
    asyncio.run(_run())


async def _run() -> None:
    from apps.api.core.database import get_db_context
    from apps.api.models import CrawlRun
    from sqlalchemy import select, func

    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=1)

    async with get_db_context() as db:
        rows = await db.execute(
            select(
                CrawlRun.source_platform,
                func.sum(CrawlRun.jobs_found).label("found"),
                func.sum(CrawlRun.jobs_failed).label("failed"),
            )
            .where(CrawlRun.started_at > cutoff)
            .group_by(CrawlRun.source_platform)
        )
        for row in rows:
            total = (row.found or 0) + (row.failed or 0)
            if total == 0:
                continue
            rate = (row.found or 0) / total
            if rate < 0.70:
                _alert(row.source_platform, rate, "CRITICAL — auto-pausing")
                # TODO Phase E: set adapter enabled=False in DB config
            elif rate < 0.85:
                _alert(row.source_platform, rate, "WARNING")


def _alert(source: str, rate: float, level: str) -> None:
    # TODO Phase E: wire to Slack webhook or email
    logger.warning(
        "Crawler health %s: source=%s success_rate=%.1f%%",
        level,
        source,
        rate * 100,
    )
