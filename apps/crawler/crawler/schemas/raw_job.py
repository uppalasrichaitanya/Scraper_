from pydantic import BaseModel
from typing import Optional


class RawJobSchema(BaseModel):
    source_platform: str
    source_url: str
    title: str
    company_name: str
    location_raw: Optional[str] = None
    description_raw: Optional[str] = None
    salary_raw: Optional[str] = None
    job_type_raw: Optional[str] = None
    is_remote: bool = False
    skills_raw: list[str] = []
    posted_at_raw: Optional[str] = None
    extra: dict = {}  # catch-all for source-specific fields
