"""
crawler/notifications/email.py
Email delivery via Resend SDK.
Falls back to a log-only mode when EMAIL_ENABLED=false (dev default).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy import so the crawler container doesn't hard-fail if resend isn't
# installed yet (dev environments without the package).
try:
    import resend as _resend_sdk
    _RESEND_AVAILABLE = True
except ImportError:
    _RESEND_AVAILABLE = False
    logger.warning("resend package not installed — email sending disabled")

try:
    from jinja2 import Environment, FileSystemLoader
    _TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "email"
    _jinja_env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=True)
    _JINJA_AVAILABLE = True
except ImportError:
    _JINJA_AVAILABLE = False
    logger.warning("jinja2 not installed — email templates disabled")


def _is_email_enabled() -> bool:
    return os.getenv("EMAIL_ENABLED", "false").lower() == "true"


def _get_api_key() -> Optional[str]:
    return os.getenv("RESEND_API_KEY")


def send_job_alert_email(
    to_email: str,
    user_name: str,
    jobs: list[dict],
    alert_name: str,
    alert_id: str,
) -> bool:
    """
    Send a job alert digest email.

    Args:
        to_email:   Recipient email address.
        user_name:  Display name for the greeting.
        jobs:       List of job dicts (title, company_name, location_city,
                    salary_min, salary_max, salary_currency, apply_url).
        alert_name: Human-readable alert name for the subject line.
        alert_id:   UUID string used to build the unsubscribe link.

    Returns:
        True if the email was sent (or accepted by Resend), False otherwise.
    """
    if not _is_email_enabled():
        logger.info(
            "email_skipped_disabled",
            extra={"to": to_email, "alert": alert_name, "job_count": len(jobs)},
        )
        return False

    if not _RESEND_AVAILABLE:
        logger.error("email_send_failed: resend package missing")
        return False

    api_key = _get_api_key()
    if not api_key:
        logger.error("email_send_failed: RESEND_API_KEY not set")
        return False

    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    unsubscribe_url = f"{frontend_url}/alerts/{alert_id}/unsubscribe"

    html = _render_template(
        "job_alert.html",
        user_name=user_name,
        jobs=jobs,
        alert_name=alert_name,
        unsubscribe_url=unsubscribe_url,
        frontend_url=frontend_url,
    )

    from_addr = os.getenv("EMAIL_FROM", "alerts@yourplatform.com")

    try:
        _resend_sdk.api_key = api_key
        response = _resend_sdk.Emails.send({
            "from": from_addr,
            "to": to_email,
            "subject": f"{len(jobs)} new job{'s' if len(jobs) != 1 else ''} for: {alert_name}",
            "html": html,
        })
        logger.info(
            "email_sent",
            extra={
                "to": to_email,
                "alert": alert_name,
                "job_count": len(jobs),
                "resend_id": getattr(response, "id", None),
            },
        )
        return True
    except Exception as exc:
        logger.error("email_send_failed", extra={"error": str(exc), "to": to_email})
        return False


def _render_template(template_name: str, **context: object) -> str:
    """Render a Jinja2 email template. Falls back to plain text if unavailable."""
    if not _JINJA_AVAILABLE:
        # Minimal plaintext fallback
        jobs = context.get("jobs", [])
        lines = [f"New jobs for: {context.get('alert_name', 'your alert')}\n"]
        for j in jobs:
            lines.append(f"- {j.get('title')} at {j.get('company_name', 'Unknown')}")
        lines.append(f"\nUnsubscribe: {context.get('unsubscribe_url', '')}")
        return "<pre>" + "\n".join(lines) + "</pre>"

    template = _jinja_env.get_template(template_name)
    return template.render(**context)
