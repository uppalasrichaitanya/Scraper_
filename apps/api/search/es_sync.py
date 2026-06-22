from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from elasticsearch import AsyncElasticsearch
from elasticsearch import helpers
from models.job import Job
from models.skill import JobSkill

async def bulk_index_jobs(db: AsyncSession, es: AsyncElasticsearch, batch_size: int = 500):
    offset = 0
    while True:
        stmt = (
            select(Job)
            .options(
                selectinload(Job.company),
                selectinload(Job.location),
                selectinload(Job.skills).selectinload(JobSkill.skill)
            )
            .filter(Job.status == "active")
            .offset(offset)
            .limit(batch_size)
        )
        result = await db.execute(stmt)
        jobs = result.scalars().all()
        
        if not jobs:
            break

        actions = [
            {
                "_index": "jobs",
                "_id": str(job.id),
                "_source": serialize_job_for_es(job)
            }
            for job in jobs
        ]
        await helpers.async_bulk(es, actions)
        offset += batch_size
        print(f"Indexed {offset} jobs...")

def serialize_job_for_es(job: Job) -> dict:
    return {
        "id": str(job.id),
        "title": job.title,
        "company_name": job.company.name if getattr(job, 'company', None) else None,
        "location_city": job.location.city if getattr(job, 'location', None) else None,
        "location_country": getattr(job.location, 'country', None) if getattr(job, 'location', None) else None,
        "is_remote": job.is_remote,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "salary_currency": job.currency,
        "job_type": "full_time",  # Fallback as it is missing in the model
        "skills": [js.skill.name for js in getattr(job, 'skills', []) if js.skill] if getattr(job, 'skills', None) else [],
        "description_text": job.description,
        "source_name": job.source,
        "status": job.status,
        "posted_at": job.posted_at.isoformat() if job.posted_at else None,
        "crawled_at": job.created_at.isoformat() if job.created_at else None,
        "trust_score": 0.5,
    }
