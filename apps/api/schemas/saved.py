"""
schemas/saved.py
Pydantic v2 request/response schemas for saved jobs and job alerts.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ------------------------------------------------------------------ #
#  Saved Jobs                                                          #
# ------------------------------------------------------------------ #

ApplicationStatus = Literal[
    "saved", "applied", "interviewing", "rejected", "offered"
]


class StatusUpdate(BaseModel):
    status: ApplicationStatus
    note: Optional[str] = Field(None, max_length=2000)


class SavedJobResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    status: ApplicationStatus
    note: Optional[str]
    saved_at: datetime
    updated_at: datetime

    # Embedded job summary — returned by the list endpoint
    job: Optional[JobSummary] = None

    model_config = {"from_attributes": True}


class JobSummary(BaseModel):
    """Lightweight job snapshot embedded in SavedJobResponse."""

    id: uuid.UUID
    title: str
    company_name: Optional[str]
    location_city: Optional[str]
    is_remote: bool
    salary_min: Optional[int]
    salary_max: Optional[int]
    salary_currency: Optional[str]
    job_type: Optional[str]
    apply_url: Optional[str]
    status: str  # active | stale | expired
    posted_at: Optional[datetime]

    model_config = {"from_attributes": True}


# Resolve forward reference
SavedJobResponse.model_rebuild()


# ------------------------------------------------------------------ #
#  Job Alerts                                                          #
# ------------------------------------------------------------------ #

AlertFrequency = Literal["instant", "daily", "weekly"]


class AlertQueryParams(BaseModel):
    """
    Mirrors the GET /v1/jobs query parameters exactly.
    All fields are optional — an empty dict means "all jobs".
    """

    q: Optional[str] = None
    location: Optional[str] = None
    is_remote: Optional[bool] = None
    job_type: Optional[str] = None
    skills: Optional[List[str]] = None
    salary_min: Optional[int] = None
    experience_level: Optional[str] = None


class AlertCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    frequency: AlertFrequency = "daily"
    query_params: AlertQueryParams

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class AlertResponse(BaseModel):
    id: uuid.UUID
    name: str
    frequency: AlertFrequency
    query_params: Dict[str, Any]
    last_sent_at: Optional[datetime]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
