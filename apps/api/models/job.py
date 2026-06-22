import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, Integer, Numeric, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base, utcnow


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    canonical_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False) # SHA-256 hash for deduplication
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    location_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("locations.id", ondelete="SET NULL"), index=True, nullable=True)
    
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Salary
    salary_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    
    # Source info
    source: Mapped[str] = mapped_column(String(50), nullable=False) # e.g., 'remoteok', 'wwr', 'naukri'
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False) # active, expired
    
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now(), nullable=False)

    # Relationships
    company: Mapped["Company"] = relationship(back_populates="jobs") # type: ignore
    location: Mapped[Optional["Location"]] = relationship(back_populates="jobs") # type: ignore
    skills: Mapped[list["JobSkill"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    versions: Mapped[list["JobVersion"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class JobVersion(Base):
    """Stores historical versions of a job listing for tracking changes over time."""
    __tablename__ = "job_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)
    
    job: Mapped["Job"] = relationship(back_populates="versions")
