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
from services.salary_service import (
    get_salary_stats,
    get_top_role_city_combinations,
    get_cities_for_role,
)

router = APIRouter(prefix="/v1/salaries", tags=["salaries"])


@router.get(
    "/top-combinations",
    summary="Get top role and city combinations with median salary",
)
async def top_combinations(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    combinations = await get_top_role_city_combinations(db, limit=limit)
    return {"combinations": combinations}


@router.get(
    "/{role}/cities",
    summary="Get cities for a role with median salary",
)
async def role_cities(
    role: str,
    db: AsyncSession = Depends(get_db),
):
    cities = await get_cities_for_role(db, role_slug=role)
    return {"role": role, "cities": cities}


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
