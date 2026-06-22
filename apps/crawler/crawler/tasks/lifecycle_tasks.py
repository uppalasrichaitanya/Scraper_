"""
crawler/tasks/lifecycle_tasks.py
Nightly stale job detection and expiry.

Timeline:
  0 days   → job crawled, status = active
  14 days  → last_crawled_at not updated → status = stale
  44 days  → still stale → status = expired
             (expired rows are removed from Elasticsearch but kept in Postgres)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_STALE_AFTER_DAYS = 14
_EXPIRE_AFTER_DAYS = 44  # total from crawl date (14 stale + 30 expired window)


def _get_db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(os.environ["DATABASE_SYNC_URL"], pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    return Session()


def _get_es():
    from elasticsearch import Elasticsearch

    return Elasticsearch(os.environ.get("ELASTICSEARCH_URL", "http://elasticsearch:9200"))


def _remove_expired_from_es(expired_ids: list[str]) -> None:
    """
    Remove a specific set of job IDs from the ES index.
    Using IDs (not delete_by_query on status) is safer — it avoids
    accidentally removing jobs that were re-activated between the DB
    update and the ES call.
    """
    if not expired_ids:
        return

    es = _get_es()
    try:
        # Bulk delete by ID
        actions = [{"delete": {"_index": "jobs", "_id": job_id}} for job_id in expired_ids]
        es.bulk(body=actions, refresh=False)
        logger.info("es_expired_removed", extra={"count": len(expired_ids)})
    except Exception as exc:
        logger.error(
            "es_expiry_removal_failed",
            extra={"error": str(exc), "ids": expired_ids[:5]},
        )


def _register():
    from ..celery_app import celery_app
    from apps.api.models import Job  # adjust to your Job model location

    @celery_app.task(name="lifecycle_tasks.mark_stale_jobs")
    def mark_stale_jobs() -> dict:
        """
        1. active  → stale  after STALE_AFTER_DAYS without a re-crawl.
        2. stale   → expired after EXPIRE_AFTER_DAYS total.
        3. Expired jobs are bulk-deleted from Elasticsearch.
        """
        now = datetime.now(timezone.utc)
        stale_cutoff = now - timedelta(days=_STALE_AFTER_DAYS)
        expire_cutoff = now - timedelta(days=_EXPIRE_AFTER_DAYS)

        db = _get_db()
        stale_count = 0
        expired_count = 0
        expired_ids: list[str] = []

        try:
            from sqlalchemy import update as sa_update

            # Step 1: active → stale
            stale_result = (
                db.execute(
                    sa_update(Job)
                    .where(
                        Job.status == "active",
                        Job.last_crawled_at < stale_cutoff,
                    )
                    .values(status="stale")
                    .returning(Job.id)
                )
            )
            stale_ids = [str(r[0]) for r in stale_result.fetchall()]
            stale_count = len(stale_ids)

            # Step 2: stale → expired (fetch IDs first for ES cleanup)
            expire_result = (
                db.execute(
                    sa_update(Job)
                    .where(
                        Job.status == "stale",
                        Job.last_crawled_at < expire_cutoff,
                    )
                    .values(status="expired")
                    .returning(Job.id)
                )
            )
            expired_ids = [str(r[0]) for r in expire_result.fetchall()]
            expired_count = len(expired_ids)

            db.commit()

        except Exception as exc:
            db.rollback()
            logger.error("lifecycle_task_failed", extra={"error": str(exc)})
            raise
        finally:
            db.close()

        # Remove expired jobs from Elasticsearch (keep Postgres rows for history)
        if expired_ids:
            _remove_expired_from_es(expired_ids)

        # Also sync stale jobs in ES — update their status field so they
        # can be filtered out from search results if desired.
        if stale_ids:
            _update_es_status(stale_ids, "stale")

        result = {
            "ran_at": now.isoformat(),
            "stale_count": stale_count,
            "expired_count": expired_count,
            "stale_cutoff_days": _STALE_AFTER_DAYS,
            "expire_cutoff_days": _EXPIRE_AFTER_DAYS,
        }
        logger.info("lifecycle_task_complete", extra=result)
        return result


    def _update_es_status(job_ids: list[str], new_status: str) -> None:
        es = _get_es()
        try:
            actions = [
                {
                    "update": {"_index": "jobs", "_id": job_id}
                }
                for job_id in job_ids
            ]
            # Interleave update actions with their source docs
            bulk_body = []
            for job_id in job_ids:
                bulk_body.append({"update": {"_index": "jobs", "_id": job_id}})
                bulk_body.append({"doc": {"status": new_status}})
            es.bulk(body=bulk_body, refresh=False)
        except Exception as exc:
            logger.error(
                "es_status_update_failed",
                extra={"error": str(exc), "status": new_status},
            )

    return mark_stale_jobs


mark_stale_jobs = _register()
