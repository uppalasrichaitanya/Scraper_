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
from models.job import Job, JobVersion
from models.company import Company, Location
from models.skill import Skill, JobSkill
from schemas.job import JobResponse, PaginatedJobsResponse

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


# ── GET /jobs ─────────────────────────────────────────────────────────────────
@router.get(
    "",
    response_model=PaginatedJobsResponse,
    summary="List jobs with cursor-based pagination",
)
async def list_jobs(
    db: DbSession,
    # Cursor pagination — cursor is the ISO timestamp of the last seen job's created_at
    cursor: Optional[str] = Query(
        None,
        description="Opaque cursor from previous response. Pass to fetch next page.",
    ),
    size: int = Query(20, ge=1, le=50, description="Items per page (max 50)"),
    # Filters
    source: Optional[str] = Query(None, description="Filter by source (e.g. remoteok, wwr)"),
    is_remote: Optional[bool] = Query(None, description="Filter remote-only jobs"),
    location: Optional[str] = Query(None, description="Filter by location name (case-insensitive)"),
    skill: Optional[str] = Query(None, description="Filter by skill name (case-insensitive)"),
    salary_min: Optional[int] = Query(None, description="Minimum salary filter (INR)"),
) -> PaginatedJobsResponse:
    stmt = _job_base_query()

    # ── Cursor decode ─────────────────────────────────────────────────────────
    # cursor encodes: "{created_at_iso}:{job_id}" so we avoid the tie-break
    # problem with identical timestamps
    if cursor:
        try:
            ts_part, id_part = cursor.rsplit(":", 1)
            from datetime import datetime
            cursor_ts = datetime.fromisoformat(ts_part)
            cursor_id = uuid.UUID(id_part)
            # Keyset: rows created strictly before the cursor, or at same
            # timestamp but with a lexicographically smaller UUID
            from sqlalchemy import or_, and_
            stmt = stmt.where(
                or_(
                    Job.created_at < cursor_ts,
                    and_(Job.created_at == cursor_ts, Job.id < cursor_id),
                )
            )
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid cursor format.",
            )

    # ── Filters ───────────────────────────────────────────────────────────────
    if source:
        stmt = stmt.where(Job.source == source)
    if is_remote is not None:
        stmt = stmt.where(Job.is_remote == is_remote)
    if salary_min is not None:
        stmt = stmt.where(Job.salary_min >= salary_min)
    if location:
        stmt = stmt.join(Job.location).where(
            Location.name.ilike(f"%{location}%")
        )
    if skill:
        stmt = stmt.join(Job.skills).join(JobSkill.skill).where(
            Skill.name.ilike(f"%{skill}%")
        )

    # Fetch size+1 to detect if there's a next page
    stmt = stmt.order_by(Job.created_at.desc(), Job.id.desc()).limit(size + 1)

    result = await db.execute(stmt)
    jobs: list[Job] = list(result.scalars().unique())

    has_next = len(jobs) > size
    if has_next:
        jobs = jobs[:size]

    # ── Build next_cursor ─────────────────────────────────────────────────────
    next_cursor: Optional[str] = None
    if has_next and jobs:
        last = jobs[-1]
        next_cursor = f"{last.created_at.isoformat()}:{last.id}"

    # ── Total count (for display only — cursor pagination doesn't need exact count) ──
    count_stmt = select(func.count()).select_from(Job).where(Job.status == "active")
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    return PaginatedJobsResponse(
        items=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        page=0,  # cursor-based has no page number
        size=size,
        has_next=has_next,
        next_cursor=next_cursor,
    )


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
