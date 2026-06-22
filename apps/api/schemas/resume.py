"""Pydantic schemas for resume upload and profile display."""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class ResumeUploadResponse(BaseModel):
    status: str = "processing"
    message: str = "Resume uploaded. Parsing will complete shortly."
    resume_key: str


class ProfileResponse(BaseModel):
    current_title: str | None = None
    years_experience: int | None = None
    skills: list[str] = Field(default_factory=list)
    education: list[dict] = Field(default_factory=list)
    experience: list[dict] = Field(default_factory=list)
    resume_s3_key: str | None = None
    parsed_at: datetime | None = None
    has_embedding: bool = False


class ParseStatusResponse(BaseModel):
    is_parsed: bool
    parsed_at: datetime | None = None
    skills_count: int = 0
    current_title: str | None = None
