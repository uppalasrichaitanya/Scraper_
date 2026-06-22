from typing import Any
from pydantic import BaseModel

class SearchRequest(BaseModel):
    q: str | None = None
    location: str | None = None
    is_remote: bool | None = None
    job_type: str | None = None
    experience_max: int | None = None
    salary_min: int | None = None
    skills: list[str] | None = None
    limit: int = 20
    offset: int = 0

class SearchHit(BaseModel):
    id: str
    title_normalized: str
    company_name: str
    location_city: str | None
    source_platform: str
    job_type: str | None
    is_remote: bool
    salary_min: int | None
    salary_max: int | None
    experience_min_years: int | None
    experience_max_years: int | None
    skill_names: list[str]
    score: float

class SearchResponse(BaseModel):
    total: int
    hits: list[SearchHit]
    limit: int
    offset: int
