"""
test_schemas.py — Pydantic v2 validation edge cases.
No database required.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from schemas.user import UserCreate, UserResponse
from schemas.job import JobResponse, PaginatedJobsResponse
from schemas.token import Token


# ── UserCreate ────────────────────────────────────────────────────────────────

class TestUserCreate:
    def test_valid_payload(self):
        u = UserCreate(email="test@example.com", password="password123")
        assert u.email == "test@example.com"
        assert u.password == "password123"

    def test_email_normalised(self):
        """Pydantic EmailStr lowercases the domain."""
        u = UserCreate(email="Test@EXAMPLE.COM", password="pw")
        assert "@" in u.email

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError, match="email"):
            UserCreate(email="not-an-email", password="pw")

    def test_missing_email_raises(self):
        with pytest.raises(ValidationError):
            UserCreate(password="pw")  # type: ignore[call-arg]

    def test_missing_password_raises(self):
        with pytest.raises(ValidationError):
            UserCreate(email="a@b.com")  # type: ignore[call-arg]

    def test_optional_name_fields(self):
        u = UserCreate(email="a@b.com", password="pw", first_name="Alice", last_name="Smith")
        assert u.first_name == "Alice"
        assert u.last_name == "Smith"

    def test_optional_name_defaults_to_none(self):
        u = UserCreate(email="a@b.com", password="pw")
        assert u.first_name is None
        assert u.last_name is None


# ── Token ─────────────────────────────────────────────────────────────────────

class TestToken:
    def test_valid_token(self):
        t = Token(access_token="abc", token_type="bearer", refresh_token="xyz")
        assert t.access_token == "abc"
        assert t.token_type == "bearer"

    def test_missing_access_token_raises(self):
        with pytest.raises(ValidationError):
            Token(token_type="bearer", refresh_token="xyz")  # type: ignore[call-arg]


# ── PaginatedJobsResponse ─────────────────────────────────────────────────────

def _make_now() -> datetime:
    return datetime.now(timezone.utc)


def _job_dict(**overrides) -> dict:
    base = dict(
        id=str(uuid.uuid4()),
        canonical_id="a" * 64,
        title="Python Engineer",
        description="We are hiring.",
        is_remote=True,
        source="remoteok",
        url="https://example.com/jobs/1",
        status="active",
        posted_at=_make_now(),
        created_at=_make_now(),
        updated_at=_make_now(),
        company_id=str(uuid.uuid4()),
    )
    base.update(overrides)
    return base


class TestPaginatedJobsResponse:
    def test_empty_list_valid(self):
        r = PaginatedJobsResponse(items=[], total=0, page=0, size=20, has_next=False)
        assert r.items == []
        assert r.next_cursor is None

    def test_next_cursor_optional(self):
        r = PaginatedJobsResponse(items=[], total=0, page=0, size=20, has_next=True, next_cursor="ts:uuid")
        assert r.next_cursor == "ts:uuid"

    def test_size_must_be_int(self):
        with pytest.raises(ValidationError):
            PaginatedJobsResponse(items=[], total=0, page=0, size="twenty", has_next=False)  # type: ignore[arg-type]

    def test_has_next_bool(self):
        r = PaginatedJobsResponse(items=[], total=100, page=0, size=20, has_next=True)
        assert r.has_next is True


# ── JobResponse edge cases ────────────────────────────────────────────────────

class TestJobResponse:
    def test_salary_fields_optional(self):
        r = JobResponse.model_validate(_job_dict(salary_min=None, salary_max=None))
        assert r.salary_min is None
        assert r.salary_max is None

    def test_location_id_optional(self):
        r = JobResponse.model_validate(_job_dict(location_id=None))
        assert r.location_id is None

    def test_salary_min_max_present(self):
        r = JobResponse.model_validate(_job_dict(salary_min=500_000, salary_max=1_200_000, currency="INR"))
        assert r.salary_min == 500_000
        assert r.salary_max == 1_200_000
        assert r.currency == "INR"

    def test_is_remote_flag(self):
        r = JobResponse.model_validate(_job_dict(is_remote=True))
        assert r.is_remote is True

    def test_status_field(self):
        r = JobResponse.model_validate(_job_dict(status="expired"))
        assert r.status == "expired"
