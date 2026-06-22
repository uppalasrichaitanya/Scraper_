import asyncio
from ..celery_app import app
from ..adapters.registry import ADAPTER_REGISTRY
from .store import store_job

@app.task(name="crawl.run_adapter", queue="crawl_playwright")
def run_adapter(source_name: str) -> None:
    adapter_cls = ADAPTER_REGISTRY.get(source_name)
    if not adapter_cls:
        raise ValueError(f"Unknown adapter: {source_name}")
    
    adapter = adapter_cls()
    if not hasattr(adapter, "crawl"):
        raise ValueError(f"Adapter {source_name} does not implement the crawl() method")
        
    jobs = asyncio.run(adapter.crawl())
    for job in jobs:
        store_job.delay(job.model_dump())
