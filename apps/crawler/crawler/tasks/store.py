"""
store.py — Celery task that normalises a raw job dict and upserts it into the DB.

All DB helper functions are defined here to avoid circular imports with the task
module. The task is kept thin; business logic lives in _upsert() and its helpers.

NOTE: The Job model uses columns: title, description, source, url, currency
      which correspond to spec fields: title_normalized, description_raw,
      source_platform, source_url, salary_currency.
"""
import asyncio
import datetime
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..celery_app import app
from ..pipeline.normalizer import normalize
from ..schemas.normalized_job import NormalizedJobSchema
from ..schemas.raw_job import RawJobSchema


@app.task(name="crawl.store_job", queue="store_default")
def store_job(raw_job_data: dict) -> None:
    raw = RawJobSchema(**raw_job_data)
    normalized = normalize(raw)
    asyncio.run(_upsert(normalized))


# ── Main upsert ───────────────────────────────────────────────────────────────

async def _upsert(job: NormalizedJobSchema) -> None:
    from apps.api.core.database import get_db_context
    from apps.api.models import Job, JobVersion

    async with get_db_context() as db:
        company = await _get_or_create_company(db, job.company_name)
        location = await _get_or_create_location(db, job.location_city)

        result = await db.execute(
            select(Job).where(Job.canonical_id == job.canonical_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            changes = _detect_changes(existing, job)
            if changes:
                version = JobVersion(
                    job_id=existing.id,
                    content_hash=job.canonical_id,
                    raw_data=_to_snapshot(existing),
                    created_at=datetime.datetime.utcnow(),
                )
                db.add(version)
                _apply_updates(existing, job)
            existing.updated_at = datetime.datetime.utcnow()
            existing.last_crawled_at = datetime.datetime.utcnow()
        else:
            new_job = Job(
                canonical_id=job.canonical_id,
                url=job.source_url,
                source=job.source_platform,
                title=job.title_normalized,
                description=job.description_raw or "",
                company_id=company.id,
                location_id=location.id if location else None,
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                currency=job.salary_currency,
                is_remote=job.is_remote,
                status="active",
                posted_at=datetime.datetime.utcnow(),
                last_crawled_at=datetime.datetime.utcnow(),
            )
            db.add(new_job)
            await db.flush()  # get new_job.id before inserting skills
            await _upsert_skills(db, new_job.id, job.skill_names)

        await db.commit()

        job_id = existing.id if existing else new_job.id
        from .search_tasks import index_single_job
        index_single_job.delay(str(job_id))


# ── DB helpers ────────────────────────────────────────────────────────────────

async def _get_or_create_company(db: AsyncSession, name: str):
    from apps.api.models import Company

    name_clean = name.strip()
    result = await db.execute(
        select(Company).where(Company.name == name_clean)
    )
    company = result.scalar_one_or_none()
    if not company:
        company = Company(name=name_clean)
        db.add(company)
        await db.flush()
    return company


async def _get_or_create_location(db: AsyncSession, city: str | None):
    if not city:
        return None
    from apps.api.models import Location

    result = await db.execute(
        select(Location).where(Location.city == city)
    )
    loc = result.scalar_one_or_none()
    if not loc:
        loc = Location(name=city, city=city, country="IN")
        db.add(loc)
        await db.flush()
    return loc


async def _upsert_skills(
    db: AsyncSession, job_id: uuid.UUID, skill_names: list[str]
) -> None:
    from apps.api.models import Skill, JobSkill

    # Clear existing skill links so we get a clean update
    await db.execute(delete(JobSkill).where(JobSkill.job_id == job_id))
    for name in skill_names:
        result = await db.execute(select(Skill).where(Skill.name == name))
        skill = result.scalar_one_or_none()
        if skill:
            db.add(JobSkill(job_id=job_id, skill_id=skill.id, is_required=True))


# ── Change detection helpers ──────────────────────────────────────────────────

def _detect_changes(existing, normalized: NormalizedJobSchema) -> dict:
    """Return dict of fields that changed between the stored job and fresh data."""
    changes: dict = {}
    # Map normalized schema fields → Job model columns
    field_map = {
        "title_normalized": "title",
        "salary_min": "salary_min",
        "salary_max": "salary_max",
        "is_remote": "is_remote",
    }
    for schema_field, model_col in field_map.items():
        old_val = getattr(existing, model_col, None)
        new_val = getattr(normalized, schema_field, None)
        if old_val != new_val:
            changes[schema_field] = {"old": old_val, "new": new_val}
    return changes


def _to_snapshot(job) -> dict:
    """Serialise the current job state for JobVersion.raw_data."""
    return {
        "title": job.title,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "currency": job.currency,
        "status": job.status,
        "is_remote": job.is_remote,
    }


def _apply_updates(existing, normalized: NormalizedJobSchema) -> None:
    """Overwrite mutable job fields with freshly normalised values."""
    existing.title = normalized.title_normalized
    existing.salary_min = normalized.salary_min
    existing.salary_max = normalized.salary_max
    existing.is_remote = normalized.is_remote
    existing.description = normalized.description_raw or existing.description
