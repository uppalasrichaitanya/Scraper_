import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from .company import CompanyResponse, LocationResponse


class JobBase(BaseModel):
    title: str
    description: str
    is_remote: bool
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: Optional[str] = None
    source: str
    url: str
    status: str
    posted_at: datetime


class JobResponse(JobBase):
    id: uuid.UUID
    canonical_id: str
    company_id: uuid.UUID
    location_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    company: Optional[CompanyResponse] = None
    location: Optional[LocationResponse] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedJobsResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    size: int
    has_next: bool
    next_cursor: Optional[str] = None  # pass back to ?cursor= for next page
