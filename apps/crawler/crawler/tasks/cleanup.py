"""
cleanup.py — Mark jobs stale after 14 days unseen, remove after 44 days stale.
"""
import asyncio
import datetime

from ..celery_app import app


@app.task(name="jobs.cleanup_stale")
def cleanup_stale() -> None:
    asyncio.run(_run())


async def _run() -> None:
    from apps.api.core.database import get_db_context
    from apps.api.models import Job
    from sqlalchemy import update

    cutoff_stale = datetime.datetime.utcnow() - datetime.timedelta(days=14)
    cutoff_remove = datetime.datetime.utcnow() - datetime.timedelta(days=44)

    async with get_db_context() as db:
        # Active jobs not seen in 14 days → stale
        await db.execute(
            update(Job)
            .where(Job.updated_at < cutoff_stale, Job.status == "active")
            .values(status="stale")
        )
        # Stale jobs not seen in 44 days total → removed
        await db.execute(
            update(Job)
            .where(Job.updated_at < cutoff_remove, Job.status == "stale")
            .values(status="removed")
        )
        await db.commit()
