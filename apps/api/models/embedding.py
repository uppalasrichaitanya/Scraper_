"""
models/embedding.py — Job embedding storage for hybrid vector search.

Each job gets a 384-dim embedding from all-MiniLM-L6-v2 (sentence-transformers).
Stored separately from the jobs table to avoid bloating non-vector queries.
"""
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID

from .base import Base, utcnow


class JobEmbedding(Base):
    __tablename__ = "job_embeddings"

    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # embedding column is vector(384) — managed via raw SQL in migration
    # Access via: SELECT embedding FROM job_embeddings WHERE job_id = :id
    model: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="all-MiniLM-L6-v2"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )

    job: Mapped["Job"] = relationship()  # type: ignore
