"""
crawler/tasks/alert_tasks.py
Celery tasks for job alert email dispatch.

Two tasks:
  dispatch_alerts(frequency)  — fan-out, one task per active alert
  process_single_alert(id)    — run ES query, email, update dedup state
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from celery import shared_task
from elasticsearch import Elasticsearch

from ..celery_app import celery_app
from ..notifications.email import send_job_alert_email

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
#  DB session helper (sync — consistent with existing store.py pattern) #
# ------------------------------------------------------------------ #

def _get_db():
    """Return a sync SQLAlchemy session. Caller must close it."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(os.environ["DATABASE_SYNC_URL"], pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    return Session()


def _get_es() -> Elasticsearch:
    return Elasticsearch(os.environ.get("ELASTICSEARCH_URL", "http://elasticsearch:9200"))


# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #

def _run_es_query(query_params: dict[str, Any], exclude_ids: list[str]) -> list[dict]:
    """
    Replay the same Elasticsearch query used by GET /v1/jobs.
    Returns up to 20 matching jobs not already in exclude_ids.
    """
    es = _get_es()

    must_clauses = []
    filter_clauses = [{"term": {"status": "active"}}]

    q = query_params.get("q")
    if q:
        must_clauses.append({
            "multi_match": {
                "query": q,
                "fields": ["title^3", "company_name^2", "description_text", "skills^2"],
                "type": "best_fields",
                "fuzziness": "AUTO",
            }
        })

    location = query_params.get("location")
    if location:
        filter_clauses.append({"term": {"location_city": location}})

    is_remote = query_params.get("is_remote")
    if is_remote is not None:
        filter_clauses.append({"term": {"is_remote": bool(is_remote)}})

    job_type = query_params.get("job_type")
    if job_type:
        filter_clauses.append({"term": {"job_type": job_type}})

    skills = query_params.get("skills")
    if skills:
        filter_clauses.append({"terms": {"skills": skills}})

    salary_min = query_params.get("salary_min")
    if salary_min:
        filter_clauses.append({"range": {"salary_min": {"gte": int(salary_min)}}})

    # Exclude jobs already sent in the previous batch
    if exclude_ids:
        filter_clauses.append({"bool": {"must_not": {"ids": {"values": exclude_ids}}}})

    body = {
        "query": {
            "bool": {
                "must": must_clauses if must_clauses else [{"match_all": {}}],
                "filter": filter_clauses,
            }
        },
        "sort": [{"posted_at": "desc"}],
        "size": 20,
        "_source": [
            "id", "title", "company_name", "location_city", "is_remote",
            "salary_min", "salary_max", "salary_currency", "job_type", "apply_url",
        ],
    }

    try:
        result = es.search(index="jobs", body=body)
        hits = result["hits"]["hits"]
        return [h["_source"] for h in hits]
    except Exception as exc:
        logger.error("es_query_failed_in_alert", extra={"error": str(exc)})
        return []


# ------------------------------------------------------------------ #
#  Task 1: Fan-out — one call per active alert with matching frequency  #
# ------------------------------------------------------------------ #

@celery_app.task(name="alert_tasks.dispatch_alerts")
def dispatch_alerts(frequency: str) -> dict:
    """
    Called by Celery Beat (daily at 08:00 IST, weekly on Monday 08:00 IST).
    Queries all active alerts matching the given frequency and fans out.
    """
    from apps.api.models import JobAlert  # local import to avoid circular deps

    db = _get_db()
    try:
        alerts = (
            db.query(JobAlert)
            .filter(JobAlert.is_active == True, JobAlert.frequency == frequency)
            .all()
        )
        alert_ids = [str(a.id) for a in alerts]
        logger.info("dispatching_alerts", extra={"frequency": frequency, "count": len(alert_ids)})
    finally:
        db.close()

    for alert_id in alert_ids:
        process_single_alert.delay(alert_id)

    return {"frequency": frequency, "dispatched": len(alert_ids)}


# ------------------------------------------------------------------ #
#  Task 2: Process one alert — query ES, email, update dedup state     #
# ------------------------------------------------------------------ #

@celery_app.task(
    name="alert_tasks.process_single_alert",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def process_single_alert(self, alert_id: str) -> dict:
    """
    For a single alert:
    1. Load alert + user from DB.
    2. Run the stored query_params against ES, excluding last_job_ids.
    3. If new jobs found, send email.
    4. Update last_sent_at and last_job_ids.
    """
    from apps.api.models import JobAlert, User

    db = _get_db()
    try:
        alert = db.query(JobAlert).filter(JobAlert.id == alert_id).first()
        if not alert or not alert.is_active:
            logger.info("alert_skipped", extra={"alert_id": alert_id})
            return {"skipped": True}

        user = db.query(User).filter(User.id == alert.user_id).first()
        if not user:
            logger.warning("alert_user_not_found", extra={"alert_id": alert_id})
            return {"skipped": True}

        exclude_ids = list(alert.last_job_ids or [])

    finally:
        db.close()

    # Run ES query outside the DB session (network call, don't hold connection)
    new_jobs = _run_es_query(alert.query_params, exclude_ids=exclude_ids)

    if not new_jobs:
        logger.info("alert_no_new_jobs", extra={"alert_id": alert_id})
        return {"sent": False, "reason": "no_new_jobs"}

    # Send email
    sent = send_job_alert_email(
        to_email=user.email,
        user_name=getattr(user, "name", user.email.split("@")[0]),
        jobs=new_jobs,
        alert_name=alert.name,
        alert_id=alert_id,
    )

    # Update dedup state regardless of email success (avoid hammering on retry)
    db = _get_db()
    try:
        db.query(JobAlert).filter(JobAlert.id == alert_id).update({
            "last_sent_at": datetime.now(timezone.utc),
            # Keep a rolling window of the 100 most recent job IDs
            "last_job_ids": ([j["id"] for j in new_jobs] + exclude_ids)[:100],
        })
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("alert_update_failed", extra={"alert_id": alert_id, "error": str(exc)})
        raise self.retry(exc=exc)
    finally:
        db.close()

    return {"sent": sent, "job_count": len(new_jobs), "alert_id": alert_id}
