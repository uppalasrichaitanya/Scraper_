"""
fetch_detail.py — Fetch a URL and dispatch parsed jobs to store_job tasks.
"""
import asyncio
import random

import httpx

from ..celery_app import app
from ..adapters.registry import get_adapter

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
]


def _random_ua() -> str:
    return random.choice(_USER_AGENTS)


@app.task(
    name="crawl.fetch_and_parse",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    soft_time_limit=300,
    time_limit=480,
    queue="crawl_default",
)
def fetch_and_parse(self, source: str, url: str) -> None:
    try:
        adapter = get_adapter(source)
        headers = {"User-Agent": _random_ua()}

        with httpx.Client(timeout=30, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()

        raw_jobs = asyncio.run(adapter.parse_job(resp.text, url))
        if not raw_jobs:
            return

        for raw_job in raw_jobs:
            app.send_task(
                "crawl.store_job",
                kwargs={"raw_job_data": raw_job.model_dump()},
                queue="crawl_default",
            )

    except Exception as exc:
        raise self.retry(exc=exc)
