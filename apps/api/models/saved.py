"""
models/saved.py
SavedJob and JobAlert SQLAlchemy models (Phase E).
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base  # adjust import path to match your project


class SavedJob(Base):
    __tablename__ = "saved_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    note = Column(Text, nullable=True)  # user's private note on this job
    status = Column(
        String(20),
        nullable=False,
        default="saved",
        # Allowed values: saved | applied | interviewing | rejected | offered
    )
    saved_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    user = relationship("User", back_populates="saved_jobs")
    job = relationship("Job", back_populates="saved_by_users")

    __table_args__ = (
        # A user can only save a given job once
        UniqueConstraint("user_id", "job_id", name="uq_saved_jobs_user_job"),
        # Fast lookup of all saved jobs for a user, newest first
        Index("idx_saved_jobs_user_date", "user_id", "saved_at"),
        # Kanban-style filtering by application status
        Index("idx_saved_jobs_user_status", "user_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<SavedJob user={self.user_id} job={self.job_id} status={self.status}>"


class JobAlert(Base):
    __tablename__ = "job_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(100), nullable=False)

    # Mirrors the GET /v1/jobs query params exactly.
    # Stored as JSONB so we can replay the search without schema changes.
    # Example: {"q": "python", "is_remote": true, "job_type": "full_time"}
    query_params = Column(JSONB, nullable=False)

    frequency = Column(
        String(10),
        nullable=False,
        default="daily",
        # Allowed values: instant | daily | weekly
    )

    last_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Array of job IDs included in the last dispatch.
    # Prevents resending the same listings in the next batch.
    last_job_ids = Column(ARRAY(String), nullable=False, default=list)

    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="job_alerts")

    __table_args__ = (
        Index("idx_alerts_user", "user_id"),
        # The beat task queries on (is_active, frequency) to find pending alerts
        Index("idx_alerts_dispatch", "is_active", "frequency", "last_sent_at"),
    )

    def __repr__(self) -> str:
        return f"<JobAlert user={self.user_id} name={self.name!r} freq={self.frequency}>"
