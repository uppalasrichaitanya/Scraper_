import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base, utcnow


class Skill(Base):
    """Canonical taxonomy of skills (e.g., 'Python', 'React', 'Docker')."""
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True) # e.g., 'language', 'framework', 'database'
    
    # List of alternative names/aliases to match against in descriptions (e.g., ["ReactJS", "React.js"])
    aliases: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]", nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)

    job_skills: Mapped[list["JobSkill"]] = relationship(back_populates="skill", cascade="all, delete-orphan")


class JobSkill(Base):
    """Association table linking Jobs to Skills with metadata."""
    __tablename__ = "job_skills"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False)
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True, nullable=False)
    
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)

    job: Mapped["Job"] = relationship(back_populates="skills") # type: ignore
    skill: Mapped["Skill"] = relationship(back_populates="job_skills")
