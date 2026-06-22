"""
crawler/tasks/health_tasks.py
Hourly adapter health check.

Computes parse success rate per source over the last 4 hours.
Sends a Slack alert if any source drops below the configured threshold.
Replaces the existing health_check.py stub.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Threshold below which we consider a crawler "broken"
_DEFAULT_THRESHOLD = float(os.getenv("HEALTH_ALERT_THRESHOLD", "0.85"))
_WINDOW_HOURS = 4


def _get_db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(os.environ["DATABASE_SYNC_URL"], pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    return Session()


def _send_slack_alert(message: str) -> None:
    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        logger.warning("slack_webhook_not_configured — alert logged only")
        logger.warning("HEALTH_ALERT | %s", message)
        return

    try:
        import httpx
        httpx.post(webhook_url, json={"text": message}, timeout=5)
    except Exception as exc:
        logger.error("slack_send_failed", extra={"error": str(exc)})


def _compute_success_rate(items_found: int, items_added: int) -> Optional[float]:
    """Return success rate or None if the run had no data to evaluate."""
    if not items_found:
        return None
    return items_added / items_found


# ------------------------------------------------------------------ #
#  Celery task                                                          #
# ------------------------------------------------------------------ #

def _register():
    """Import inside a function to avoid circular imports at module load."""
    from ..celery_app import celery_app
    from apps.api.models import CrawlRun  # adjust import to your model location

    @celery_app.task(name="health_tasks.check_adapter_health")
    def check_adapter_health() -> dict:
        """
        Queries CrawlRun for the last N hours.
        Alerts if any adapter's success rate drops below the threshold.
        Returns a summary dict for Celery result inspection.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=_WINDOW_HOURS)
        db = _get_db()
        alerts_fired = []

        try:
            recent_runs = (
                db.query(CrawlRun)
                .filter(CrawlRun.started_at >= cutoff)
                .all()
            )
        finally:
            db.close()

        if not recent_runs:
            logger.info("health_check: no crawl runs in the last %dh", _WINDOW_HOURS)
            return {"checked": 0, "alerts": []}

        # Aggregate by source (a source may have multiple runs in the window)
        from collections import defaultdict
        by_source: dict[str, dict] = defaultdict(lambda: {"fetched": 0, "added": 0})

        for run in recent_runs:
            source = getattr(run, "source", None) or getattr(run, "source_name", "unknown")
            by_source[source]["fetched"] += run.items_found or 0
            by_source[source]["added"] += run.items_added or 0

        for source, counts in by_source.items():
            rate = _compute_success_rate(counts["fetched"], counts["added"])
            if rate is None:
                logger.info(
                    "health_check_skip",
                    extra={"source": source, "reason": "no_items_found"},
                )
                continue

            log_extra = {
                "source": source,
                "success_rate": f"{rate:.1%}",
                "fetched": counts["fetched"],
                "added": counts["added"],
                "threshold": f"{_DEFAULT_THRESHOLD:.1%}",
            }

            if rate < _DEFAULT_THRESHOLD:
                message = (
                    f"⚠️ *Crawler health alert* — `{source}`\n"
                    f"Parse success rate: *{rate:.0%}* "
                    f"({counts['added']}/{counts['fetched']} items)\n"
                    f"Threshold: {_DEFAULT_THRESHOLD:.0%} | Window: last {_WINDOW_HOURS}h\n"
                    f"Check: `apps/crawler/crawler/adapters/{source}.py` for selector drift."
                )
                logger.error("health_alert_fired", extra=log_extra)
                _send_slack_alert(message)
                alerts_fired.append({"source": source, "rate": rate})
            else:
                logger.info("health_check_ok", extra=log_extra)

        return {
            "checked": len(by_source),
            "alerts": alerts_fired,
            "window_hours": _WINDOW_HOURS,
        }

    return check_adapter_health


check_adapter_health = _register()
