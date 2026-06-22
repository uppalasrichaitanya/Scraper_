"""
discover.py — Enqueue fetch_and_parse tasks for all registered adapters.

Uses app.send_task() with the string task name instead of importing fetch_detail
directly, which would create a circular import (discover → fetch_detail → store →
… → celery_app → discover).
"""
from ..celery_app import app
from ..adapters.registry import ADAPTER_REGISTRY


@app.task(name="crawl.discover", queue="crawl_default")
def discover_all() -> None:
    """Enqueue fetch_and_parse tasks for every URL from every registered adapter."""
    for source_name, adapter_cls in ADAPTER_REGISTRY.items():
        adapter = adapter_cls()
        for url in adapter.get_listing_urls():
            app.send_task(
                "crawl.fetch_and_parse",
                kwargs={"source": source_name, "url": url},
                queue="crawl_default",
            )
