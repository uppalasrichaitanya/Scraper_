"""
routers/v1/salary.py — Salary intelligence endpoints.

Endpoints:
  GET /v1/salaries/{role}          — salary stats for a role
  GET /v1/salaries/{role}/{city}   — salary stats for role + city
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas.salary import SalaryStatsResponse
from services.salary_service import get_salary_stats

router = APIRouter(prefix="/v1/salaries", tags=["salaries"])


@router.get(
    "/{role}",
    response_model=SalaryStatsResponse,
    summary="Get salary statistics for a role",
)
async def salary_by_role(
    role: str,
    db: AsyncSession = Depends(get_db),
):
    stats = await get_salary_stats(db, role)
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Not enough salary data for role '{role}'. Need at least 5 data points.",
        )
    return SalaryStatsResponse(**stats)


@router.get(
    "/{role}/{city}",
    response_model=SalaryStatsResponse,
    summary="Get salary statistics for a role in a specific city",
)
async def salary_by_role_and_city(
    role: str,
    city: str,
    db: AsyncSession = Depends(get_db),
):
    stats = await get_salary_stats(db, role, city)
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Not enough salary data for '{role}' in '{city}'. Need at least 5 data points.",
        )
    return SalaryStatsResponse(**stats)
