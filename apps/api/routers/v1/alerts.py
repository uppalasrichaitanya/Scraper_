"""
routers/v1/alerts.py
Job alert endpoints — create, list, delete (soft).
All endpoints require authentication.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db
from models.saved import JobAlert
from models.user import User
from schemas.saved import AlertCreate, AlertResponse

router = APIRouter(prefix="/v1/alerts", tags=["alerts"])


# ------------------------------------------------------------------ #
#  POST /v1/alerts  — create alert                                     #
# ------------------------------------------------------------------ #

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=AlertResponse,
    summary="Create a saved search alert",
)
async def create_alert(
    body: AlertCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Cap at 10 active alerts per user to prevent runaway email volume
    count_result = await db.execute(
        select(JobAlert)
        .where(JobAlert.user_id == current_user.id, JobAlert.is_active == True)
    )
    existing_count = len(count_result.scalars().all())
    if existing_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum of 10 active alerts allowed per user.",
        )

    alert = JobAlert(
        user_id=current_user.id,
        name=body.name,
        # Exclude None values so JSONB stays clean
        query_params={k: v for k, v in body.query_params.model_dump().items() if v is not None},
        frequency=body.frequency,
        last_job_ids=[],
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


# ------------------------------------------------------------------ #
#  GET /v1/alerts  — list active alerts                                #
# ------------------------------------------------------------------ #

@router.get(
    "",
    response_model=list[AlertResponse],
    summary="List the current user's active job alerts",
)
async def list_alerts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(JobAlert)
        .where(JobAlert.user_id == current_user.id, JobAlert.is_active == True)
        .order_by(JobAlert.created_at.desc())
    )
    return result.scalars().all()


# ------------------------------------------------------------------ #
#  DELETE /v1/alerts/{id}  — soft delete                               #
# ------------------------------------------------------------------ #

@router.delete(
    "/{alert_id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate a job alert",
)
async def delete_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        update(JobAlert)
        .where(
            JobAlert.id == alert_id,
            JobAlert.user_id == current_user.id,  # ownership check
            JobAlert.is_active == True,
        )
        .values(is_active=False)
        .returning(JobAlert.id)
    )
    deactivated_id = result.scalar_one_or_none()

    if not deactivated_id:
        raise HTTPException(status_code=404, detail="Alert not found or already inactive")

    await db.commit()
    return {"deleted": True, "alert_id": str(alert_id)}
