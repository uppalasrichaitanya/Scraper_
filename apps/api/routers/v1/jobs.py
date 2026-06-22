"""
jobs.py — Jobs read router.

Endpoints:
  GET /v1/jobs        — cursor-based paginated list with filters
  GET /v1/jobs/{id}   — single job with company + skill joins
"""

from __future__ import annotations

import uuid
from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.config import settings
from core.database import get_db
from core.deps import get_optional_user
from models.job import Job, JobVersion
from models.user import User
from models.company import Company, Location
from models.skill import Skill, JobSkill
from schemas.job import JobResponse, PaginatedJobsResponse
from elasticsearch import AsyncElasticsearch
from core.elasticsearch import get_es

logger = structlog.get_logger(__name__)
router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]


def _job_base_query():
    """Base query for fetching jobs with eager-loaded relations."""
    return (
        select(Job)
        .options(
            selectinload(Job.company),
            selectinload(Job.location),
            selectinload(Job.skills).selectinload(JobSkill.skill),
        )
        .where(Job.status == "active")
    )


@router.get(
    "",
    summary="List jobs using Elasticsearch (supports hybrid semantic mode)",
)
async def search_jobs(
    q: str | None = None,
    location: str | None = None,
    is_remote: bool | None = None,
    job_type: str | None = None,
    skills: list[str] = Query(default=[]),
    salary_min: int | None = None,
    page: int = 1,
    page_size: int = 20,
    mode: str | None = None,  # "hybrid" for semantic + keyword search
    es: AsyncElasticsearch = Depends(get_es),
    user: User | None = Depends(get_optional_user),
):
    # ── Hybrid search mode (Phase F) ──────────────────────────────────────
    if mode == "hybrid" and q:
        from services.search_service import hybrid_search, get_user_embedding

        user_embedding = None
        if user:
            user_embedding = await get_user_embedding(str(user.id))

        filters = {}
        if location:
            filters["location"] = location
        if is_remote is not None:
            filters["is_remote"] = is_remote
        if skills:
            filters["skills"] = skills
        if salary_min:
            filters["salary_min"] = salary_min

        return await hybrid_search(
            q=q,
            filters=filters,
            user_embedding=user_embedding,
            page=page,
            page_size=page_size,
        )

    # ── Standard ES keyword search ────────────────────────────────────────
    must_clauses = []
    filter_clauses = [{"term": {"status": "active"}}]

    if q:
        must_clauses.append({
            "multi_match": {
                "query": q,
                "fields": ["title^3", "company_name^2", "description_text", "skills^2"],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        })

    if location:
        filter_clauses.append({"term": {"location_city": location}})
    if is_remote is not None:
        filter_clauses.append({"term": {"is_remote": is_remote}})
    if job_type:
        filter_clauses.append({"term": {"job_type": job_type}})
    if skills:
        filter_clauses.append({"terms": {"skills": skills}})
    if salary_min:
        filter_clauses.append({"range": {"salary_min": {"gte": salary_min}}})

    body = {
        "query": {"bool": {"must": must_clauses or [{"match_all": {}}], "filter": filter_clauses}},
        "sort": [{"_score": "desc"}, {"posted_at": "desc"}],
        "from": (page - 1) * page_size,
        "size": page_size,
        "track_total_hits": True,
    }

    result = await es.search(index="jobs", body=body)
    hits = result["hits"]["hits"]
    total = result["hits"]["total"]["value"]

    # If user is authenticated, try to inject match_scores
    items = [h["_source"] for h in hits]
    if user and items:
        try:
            from services.search_service import get_user_embedding
            user_emb = await get_user_embedding(str(user.id))
            if user_emb:
                from sqlalchemy import text as sa_text
                from core.database import AsyncSessionLocal

                job_ids = [item.get("id") for item in items if item.get("id")]
                if job_ids:
                    user_emb_str = "[" + ",".join(str(v) for v in user_emb) + "]"
                    async with AsyncSessionLocal() as db:
                        match_result = await db.execute(
                            sa_text("""
                                SELECT je.job_id::text, 1 - (je.embedding <=> :user_emb) AS match_score
                                FROM job_embeddings je
                                WHERE je.job_id::text = ANY(:job_ids)
                            """),
                            {"user_emb": user_emb_str, "job_ids": job_ids},
                        )
                        scores = {row["job_id"]: max(0.0, min(1.0, float(row["match_score"])))
                                  for row in match_result.mappings()}
                        for item in items:
                            item["match_score"] = scores.get(item.get("id"))
        except Exception:
            pass  # Match scoring is best-effort

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
        "has_next": total > (page * page_size)
    }


# ── GET /jobs/{id} ────────────────────────────────────────────────────────────
@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get a single job by ID",
)
async def get_job(
    job_id: uuid.UUID,
    db: DbSession,
) -> JobResponse:
    stmt = _job_base_query().where(Job.id == job_id)
    result = await db.execute(stmt)
    job: Job | None = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found.",
        )

    return JobResponse.model_validate(job)
