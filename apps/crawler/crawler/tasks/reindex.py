from ..celery_app import app
import asyncio
from apps.api.core.database import get_db_context
from apps.api.services.es_sync import bulk_reindex

@app.task(name="jobs.reindex_elasticsearch", queue="cleanup_default")
def reindex_elasticsearch() -> None:
    """Full reindex from PostgreSQL to Elasticsearch. Run as nightly Celery task."""
    async def run_reindex():
        async with get_db_context() as db:
            total = await bulk_reindex(db)
            from structlog import get_logger
            logger = get_logger()
            logger.info("Bulk reindex complete", total_indexed=total)
            
    asyncio.run(run_reindex())
