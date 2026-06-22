"""Pydantic schemas for salary intelligence endpoints."""
from __future__ import annotations

from pydantic import BaseModel


class SalaryStatsResponse(BaseModel):
    role: str
    city: str | None = None
    p25: int | None = None
    median: int | None = None
    p75: int | None = None
    avg: int | None = None
    sample_size: int = 0
