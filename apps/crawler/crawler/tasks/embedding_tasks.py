"""
tasks/embedding_tasks.py — Generate and store job embeddings.

Uses sentence-transformers all-MiniLM-L6-v2 (384-dim).
Called after ES indexing for each new/updated job, and via backfill for existing jobs.
"""
import asyncio
import logging
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="embedding.generate_job_embedding", bind=True, max_retries=3, default_retry_delay=30)
def generate_job_embedding(self, job_id: str):
    """Generate embedding for a single job and store in job_embeddings."""
    asyncio.run(_generate_single(job_id))


@app.task(name="embedding.backfill_job_embeddings")
def backfill_job_embeddings(batch_size: int = 100):
    """Generate embeddings for all active jobs that don't have one yet."""
    asyncio.run(_backfill(batch_size))


async def _generate_single(job_id: str):
    from apps.api.core.database import get_db_context
    from apps.api.models.job import Job
    from apps.api.models.skill import JobSkill
    from apps.api.services.embedding_service import embed_text, build_job_text
    from sqlalchemy.orm import selectinload

    async with get_db_context() as db:
        stmt = (
            select(Job)
            .options(
                selectinload(Job.company),
                selectinload(Job.skills).selectinload(JobSkill.skill),
            )
            .where(Job.id == uuid.UUID(job_id))
        )
        result = await db.execute(stmt)
        job = result.scalar_one_or_none()
        if not job:
            logger.warning("Job %s not found for embedding", job_id)
            return

        # Build text and generate embedding
        skills = [js.skill.name for js in (job.skills or []) if js.skill]
        company_name = job.company.name if job.company else None
        text_input = build_job_text(job.title, company_name, skills, job.description)
        embedding = embed_text(text_input)

        # Upsert into job_embeddings using raw SQL (vector column)
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
        await db.execute(text("""
            INSERT INTO job_embeddings (job_id, embedding, model, created_at)
            VALUES (:job_id, :embedding, 'all-MiniLM-L6-v2', now())
            ON CONFLICT (job_id) DO UPDATE SET
                embedding = :embedding,
                model = 'all-MiniLM-L6-v2',
                created_at = now()
        """), {"job_id": job_id, "embedding": embedding_str})
        await db.commit()
        logger.info("Embedding stored for job %s", job_id)


async def _backfill(batch_size: int):
    from apps.api.core.database import get_db_context
    from apps.api.models.job import Job
    from apps.api.models.skill import JobSkill
    from apps.api.services.embedding_service import embed_batch, build_job_text
    from sqlalchemy.orm import selectinload

    async with get_db_context() as db:
        # Find jobs without embeddings
        stmt = (
            select(Job)
            .options(
                selectinload(Job.company),
                selectinload(Job.skills).selectinload(JobSkill.skill),
            )
            .where(Job.status == "active")
            .where(
                ~Job.id.in_(
                    select(text("job_id")).select_from(text("job_embeddings"))
                )
            )
            .limit(batch_size)
        )
        result = await db.execute(stmt)
        jobs = result.scalars().all()

        if not jobs:
            logger.info("Backfill complete — no more jobs without embeddings")
            return

        logger.info("Backfilling embeddings for %d jobs", len(jobs))

        # Build texts
        texts = []
        job_ids = []
        for job in jobs:
            skills = [js.skill.name for js in (job.skills or []) if js.skill]
            company_name = job.company.name if job.company else None
            texts.append(build_job_text(job.title, company_name, skills, job.description))
            job_ids.append(str(job.id))

        # Batch embed
        embeddings = embed_batch(texts)

        # Store all embeddings
        for job_id, embedding in zip(job_ids, embeddings):
            embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
            await db.execute(text("""
                INSERT INTO job_embeddings (job_id, embedding, model, created_at)
                VALUES (:job_id, :embedding, 'all-MiniLM-L6-v2', now())
                ON CONFLICT (job_id) DO UPDATE SET
                    embedding = :embedding,
                    model = 'all-MiniLM-L6-v2',
                    created_at = now()
            """), {"job_id": job_id, "embedding": embedding_str})

        await db.commit()
        logger.info("Backfilled %d job embeddings", len(jobs))

        # If there might be more, schedule another batch
        if len(jobs) == batch_size:
            backfill_job_embeddings.delay(batch_size)
