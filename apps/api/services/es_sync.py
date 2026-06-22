from apps.api.core.elasticsearch import get_es, JOBS_INDEX
from apps.api.models import Job
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


def _job_to_doc(job: Job) -> dict:
    return {
        "id":                   str(job.id),
        "title_normalized":     job.title,
        "company_name":         job.company.name if job.company else "",
        "description_raw":      job.description,
        "location_city":        job.location.city if job.location else None,
        "source_platform":      job.source,
        "job_type":             None,
        "is_remote":            job.is_remote,
        "salary_min":           job.salary_min,
        "salary_max":           job.salary_max,
        "experience_min_years": None,
        "experience_max_years": None,
        "status":               job.status,
        "skill_names":          [js.skill.name for js in (job.skills or [])],
        "first_seen_at":        job.created_at.isoformat() if job.created_at else None,
        "last_seen_at":         job.updated_at.isoformat() if job.updated_at else None,
    }


async def index_job(job: Job):
    """Index or update a single job document. Call from store.py after every upsert."""
    es = get_es()
    await es.index(
        index=JOBS_INDEX,
        id=str(job.id),
        document=_job_to_doc(job),
    )


async def delete_job(job_id: str):
    """Remove a job from the index. Call when status → removed."""
    es = get_es()
    await es.delete(index=JOBS_INDEX, id=job_id, ignore=[404])


async def bulk_reindex(db: AsyncSession, batch_size: int = 500):
    """Full reindex from PostgreSQL. Run as nightly Celery task."""
    from elasticsearch.helpers import async_bulk
    from sqlalchemy.orm import selectinload, joinedload
    from apps.api.models import JobSkill
    es = get_es()
    offset = 0
    total = 0
    while True:
        result = await db.execute(
            select(Job)
            .options(
                selectinload(Job.skills).joinedload(JobSkill.skill),
                joinedload(Job.company),
                joinedload(Job.location)
            )
            .where(Job.status == "active")
            .limit(batch_size)
            .offset(offset)
        )
        jobs = result.scalars().all()
        if not jobs:
            break
        actions = [
            {"_index": JOBS_INDEX, "_id": str(j.id), "_source": _job_to_doc(j)}
            for j in jobs
        ]
        await async_bulk(es, actions)
        total += len(jobs)
        offset += batch_size
    return total
