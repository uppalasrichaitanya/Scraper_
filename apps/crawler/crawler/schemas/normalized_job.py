from pydantic import BaseModel
from typing import Optional


class NormalizedJobSchema(BaseModel):
    canonical_id: str  # SHA-256, computed by deduplicator
    source_platform: str
    source_url: str
    title_raw: str
    title_normalized: str
    company_name: str
    location_city: Optional[str] = None
    location_country: str = "IN"
    salary_min: Optional[int] = None  # annual INR
    salary_max: Optional[int] = None
    salary_currency: str = "INR"
    salary_raw_text: Optional[str] = None
    job_type: Optional[str] = None  # full_time | contract | internship
    is_remote: bool = False
    experience_min_years: Optional[int] = None
    experience_max_years: Optional[int] = None
    skill_names: list[str] = []  # canonical names, resolved by skill_extractor
    description_raw: Optional[str] = None
