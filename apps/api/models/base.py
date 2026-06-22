from datetime import datetime, timezone
from typing import Any
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy import DateTime


class Base(DeclarativeBase):
    """Declarative Base for all SQLAlchemy models."""
    
    # Optional generic timestamps if we want them on all tables,
    # but we will define them explicitly where needed.
    type_annotation_map = {
        datetime: DateTime(timezone=True)
    }

def utcnow() -> datetime:
    return datetime.now(timezone.utc)
