import asyncio
import uuid
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ..celery_app import app

@app.task(name="search.index_single_job", bind=True, max_retries=3, default_retry_delay=10)
def index_single_job(self, job_id: str):
    from apps.api.core.database import get_db_context
    from apps.api.core.elasticsearch import get_es
    from apps.api.models.job import Job
    from apps.api.models.skill import JobSkill
    from apps.api.search.es_sync import serialize_job_for_es

    async def _index():
        es = get_es()
        async with get_db_context() as db:
            stmt = (
                select(Job)
                .options(
                    selectinload(Job.company),
                    selectinload(Job.location),
                    selectinload(Job.skills).selectinload(JobSkill.skill)
                )
                .where(Job.id == uuid.UUID(job_id))
            )
            result = await db.execute(stmt)
            job = result.scalar_one_or_none()
            if not job:
                return

            doc = serialize_job_for_es(job)
            await es.index(index="jobs", id=job_id, document=doc)

    asyncio.run(_index())

    # Also generate embedding for hybrid vector search
    try:
        from crawler.tasks.embedding_tasks import generate_job_embedding
        generate_job_embedding.delay(job_id)
    except Exception:
        pass  # Embedding generation is best-effort
