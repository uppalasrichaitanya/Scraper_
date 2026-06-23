"""
services/salary_service.py — Salary intelligence queries.

Runs percentile aggregation on active jobs with salary data.
Used by the /v1/salaries/ endpoints and the ISR salary pages.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def get_salary_stats(
    db: AsyncSession,
    role_slug: str,
    city_slug: str | None = None,
) -> dict[str, Any] | None:
    """Get salary percentiles for a role (and optional city).
    
    Returns None if sample_size < 5 (not enough data for meaningful stats).
    """
    # Convert slug to ILIKE pattern: "python-developer" → "%python%developer%"
    role_pattern = "%" + "%".join(role_slug.split("-")) + "%"

    params: dict[str, Any] = {"role_pattern": role_pattern}

    city_clause = ""
    if city_slug:
        city_pattern = "%" + "%".join(city_slug.split("-")) + "%"
        city_clause = "AND LOWER(l.city) LIKE :city_pattern"
        params["city_pattern"] = city_pattern

    query = text(f"""
        SELECT
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY j.salary_min) AS p25,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY j.salary_min) AS median,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY j.salary_min) AS p75,
            AVG(j.salary_min)::integer AS avg_salary,
            COUNT(*) AS sample_size
        FROM jobs j
        LEFT JOIN locations l ON j.location_id = l.id
        WHERE
            j.status = 'active'
            AND j.salary_min IS NOT NULL
            AND j.salary_min > 0
            AND LOWER(j.title) LIKE :role_pattern
            {city_clause}
            AND j.created_at > now() - INTERVAL '90 days'
    """)

    result = await db.execute(query, params)
    row = result.mappings().first()

    if not row or row["sample_size"] < 5:
        return None

    return {
        "role": role_slug,
        "city": city_slug,
        "p25": int(row["p25"]) if row["p25"] else None,
        "median": int(row["median"]) if row["median"] else None,
        "p75": int(row["p75"]) if row["p75"] else None,
        "avg": int(row["avg_salary"]) if row["avg_salary"] else None,
        "sample_size": row["sample_size"],
    }


async def get_top_role_city_combinations(
    db: AsyncSession,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Get the top role+city combinations by job count. Used for ISR generateStaticParams."""
    query = text("""
        SELECT
            LOWER(REGEXP_REPLACE(j.title, '[^a-zA-Z0-9 ]', '', 'g')) as role_slug,
            LOWER(l.city) as city_slug,
            COUNT(*) as count,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY j.salary_min) as median
        FROM jobs j
        LEFT JOIN locations l ON j.location_id = l.id
        WHERE j.status = 'active'
            AND j.salary_min IS NOT NULL
            AND l.city IS NOT NULL
        GROUP BY 1, 2
        ORDER BY 3 DESC
        LIMIT :limit
    """)

    result = await db.execute(query, {"limit": limit})
    rows = result.mappings().all()

    return [
        {
            "role_slug": row["role_slug"].replace(" ", "-") if row["role_slug"] else "",
            "city_slug": row["city_slug"].replace(" ", "-") if row["city_slug"] else "",
            "count": row["count"],
            "median": int(row["median"]) if row["median"] else None,
        }
        for row in rows
    ]


async def get_cities_for_role(
    db: AsyncSession,
    role_slug: str,
) -> list[dict[str, Any]]:
    """Get cities that have salary data for a given role, sorted by listing volume."""
    role_pattern = "%" + "%".join(role_slug.split("-")) + "%"
    
    query = text("""
        SELECT
            LOWER(l.city) as city_slug,
            COUNT(*) as count,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY j.salary_min) as median
        FROM jobs j
        LEFT JOIN locations l ON j.location_id = l.id
        WHERE j.status = 'active'
            AND j.salary_min IS NOT NULL
            AND l.city IS NOT NULL
            AND LOWER(j.title) LIKE :role_pattern
        GROUP BY 1
        HAVING COUNT(*) >= 30
        ORDER BY 2 DESC
    """)

    result = await db.execute(query, {"role_pattern": role_pattern})
    rows = result.mappings().all()

    return [
        {
            "city_slug": row["city_slug"].replace(" ", "-") if row["city_slug"] else "",
            "count": row["count"],
            "median": int(row["median"]) if row["median"] else None,
        }
        for row in rows
    ]

