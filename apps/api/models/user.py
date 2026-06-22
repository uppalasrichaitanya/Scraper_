import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from .base import Base, utcnow


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=func.now(), nullable=False)

    profile: Mapped["UserProfile"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    consents: Mapped[list["ConsentRecord"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    saved_jobs: Mapped[list["SavedJob"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    job_alerts: Mapped[list["JobAlert"]] = relationship(back_populates="user", cascade="all, delete-orphan")



class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # ── Phase F: Resume fields ────────────────────────────────────────────────
    current_title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    years_experience: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    skills: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)
    education: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    experience: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    resume_s3_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    parsed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    parse_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, server_default="1")
    # embedding stored as vector(384) — managed via raw SQL in migration, not mapped here
    # Access via: SELECT embedding FROM user_profiles WHERE user_id = :id

    user: Mapped["User"] = relationship(back_populates="profile")


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    
    terms_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    privacy_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="consents")
