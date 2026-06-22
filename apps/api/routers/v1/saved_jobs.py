"""
routers/v1/saved_jobs.py
Saved jobs endpoints — save, unsave, status update, list.
All endpoints require authentication.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.deps import get_current_user, get_db
from models.job import Job
from models.saved import SavedJob
from models.user import User
from schemas.saved import ApplicationStatus, SavedJobResponse, StatusUpdate

router = APIRouter(prefix="/v1/saved-jobs", tags=["saved-jobs"])


# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #

def _serialize(row: SavedJob) -> dict:
    """Build the response dict from a SavedJob ORM row."""
    job = row.job
    return {
        "id": str(row.id),
        "job_id": str(row.job_id),
        "status": row.status,
        "note": row.note,
        "saved_at": row.saved_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
        "job": {
            "id": str(job.id),
            "title": job.title,
            "company_name": job.company.name if job.company else None,
            "location_city": job.location.city if job.location else None,
            "is_remote": job.is_remote,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "salary_currency": job.salary_currency,
            "job_type": job.job_type,
            "apply_url": job.apply_url,
            "status": job.status,
            "posted_at": job.posted_at.isoformat() if job.posted_at else None,
        } if job else None,
    }


# ------------------------------------------------------------------ #
#  POST /v1/saved-jobs/{job_id}  — save a job                         #
# ------------------------------------------------------------------ #

@router.post(
    "/{job_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Save a job",
)
async def save_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify the job actually exists
    job_exists = await db.execute(select(Job.id).where(Job.id == job_id))
    if not job_exists.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Job not found")

    # Check for duplicate
    existing = await db.execute(
        select(SavedJob).where(
            SavedJob.user_id == current_user.id,
            SavedJob.job_id == job_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Job already saved")

    saved = SavedJob(user_id=current_user.id, job_id=job_id)
    db.add(saved)
    await db.commit()
    await db.refresh(saved)

    return {"saved": True, "job_id": str(job_id), "saved_job_id": str(saved.id)}


# ------------------------------------------------------------------ #
#  DELETE /v1/saved-jobs/{job_id}  — unsave                           #
# ------------------------------------------------------------------ #

@router.delete(
    "/{job_id}",
    status_code=status.HTTP_200_OK,
    summary="Unsave a job",
)
async def unsave_job(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        delete(SavedJob)
        .where(
            SavedJob.user_id == current_user.id,
            SavedJob.job_id == job_id,
        )
        .returning(SavedJob.id)
    )
    deleted_id = result.scalar_one_or_none()

    if not deleted_id:
        raise HTTPException(status_code=404, detail="Saved job not found")

    await db.commit()
    return {"saved": False, "job_id": str(job_id)}


# ------------------------------------------------------------------ #
#  PATCH /v1/saved-jobs/{job_id}/status  — update application status  #
# ------------------------------------------------------------------ #

@router.patch(
    "/{job_id}/status",
    status_code=status.HTTP_200_OK,
    summary="Update application status for a saved job",
)
async def update_job_status(
    job_id: UUID,
    body: StatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        update(SavedJob)
        .where(
            SavedJob.user_id == current_user.id,
            SavedJob.job_id == job_id,
        )
        .values(
            status=body.status,
            note=body.note if body.note is not None else SavedJob.note,
            updated_at=datetime.utcnow(),
        )
        .returning(SavedJob.id)
    )
    updated_id = result.scalar_one_or_none()

    if not updated_id:
        raise HTTPException(status_code=404, detail="Saved job not found")

    await db.commit()
    return {"updated": True, "job_id": str(job_id), "status": body.status}


# ------------------------------------------------------------------ #
#  GET /v1/saved-jobs  — list saved jobs                               #
# ------------------------------------------------------------------ #

@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="List saved jobs, optionally filtered by status",
)
async def list_saved_jobs(
    status_filter: ApplicationStatus | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(SavedJob)
        .where(SavedJob.user_id == current_user.id)
        .options(
            selectinload(SavedJob.job).selectinload(Job.company),
            selectinload(SavedJob.job).selectinload(Job.location),
        )
        .order_by(SavedJob.saved_at.desc())
    )

    if status_filter:
        q = q.where(SavedJob.status == status_filter)

    results = await db.execute(q)
    rows = results.scalars().all()

    return {
        "total": len(rows),
        "items": [_serialize(r) for r in rows],
    }
