"""
test_jobs.py — Integration tests for GET /jobs cursor-based pagination.
Requires Testcontainers (real Postgres).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.company import Company
from models.job import Job

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def _make_company(name: str = "ACME Corp") -> Company:
    return Company(id=uuid.uuid4(), name=name)


def _make_job(company_id: uuid.UUID, offset_seconds: int = 0, **overrides) -> Job:
    """Factory for test jobs with deterministic canonical_ids."""
    job_id = uuid.uuid4()
    defaults = dict(
        id=job_id,
        canonical_id=f"sha256_{job_id.hex}",
        title="Software Engineer",
        description="Join our team.",
        company_id=company_id,
        is_remote=True,
        source="remoteok",
        url=f"https://example.com/jobs/{job_id}",
        status="active",
        posted_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc) - timedelta(seconds=offset_seconds),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Job(**defaults)


class TestListJobs:
    async def test_empty_db_returns_empty_list(self, client: AsyncClient):
        resp = await client.get("/v1/jobs")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["has_next"] is False

    async def test_returns_active_jobs(self, client: AsyncClient, db: AsyncSession):
        company = _make_company()
        db.add(company)
        job = _make_job(company.id)
        db.add(job)
        await db.flush()

        resp = await client.get("/v1/jobs")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) >= 1

    async def test_expired_jobs_excluded(self, client: AsyncClient, db: AsyncSession):
        company = _make_company()
        db.add(company)
        expired = _make_job(company.id, status="expired")
        db.add(expired)
        await db.flush()

        resp = await client.get("/v1/jobs")
        items = resp.json()["items"]
        assert all(j["status"] == "active" for j in items)

    async def test_cursor_pagination_first_page(self, client: AsyncClient, db: AsyncSession):
        """Insert 5 jobs, request page_size=2, verify has_next and cursor."""
        company = _make_company()
        db.add(company)
        for i in range(5):
            db.add(_make_job(company.id, offset_seconds=i * 10))
        await db.flush()

        resp = await client.get("/v1/jobs?size=2")
        body = resp.json()
        assert len(body["items"]) == 2
        assert body["has_next"] is True
        assert body["next_cursor"] is not None

    async def test_cursor_pagination_second_page(self, client: AsyncClient, db: AsyncSession):
        """Use the cursor from page 1 to fetch page 2."""
        company = _make_company()
        db.add(company)
        for i in range(5):
            db.add(_make_job(company.id, offset_seconds=i * 10))
        await db.flush()

        r1 = await client.get("/v1/jobs?size=2")
        cursor = r1.json()["next_cursor"]
        assert cursor is not None

        r2 = await client.get("/v1/jobs", params={"size": 2, "cursor": cursor})
        body = r2.json()
        assert len(body["items"]) > 0

        # Items on page 2 should not overlap with page 1
        ids_p1 = {j["id"] for j in r1.json()["items"]}
        ids_p2 = {j["id"] for j in body["items"]}
        assert ids_p1.isdisjoint(ids_p2)

    async def test_invalid_cursor_returns_400(self, client: AsyncClient):
        resp = await client.get("/v1/jobs?cursor=GARBAGE_CURSOR")
        assert resp.status_code == 400

    async def test_filter_by_remote(self, client: AsyncClient, db: AsyncSession):
        company = _make_company()
        db.add(company)
        db.add(_make_job(company.id, is_remote=True))
        db.add(_make_job(company.id, is_remote=False))
        await db.flush()

        resp = await client.get("/v1/jobs?is_remote=true")
        items = resp.json()["items"]
        assert all(j["is_remote"] is True for j in items)

    async def test_size_limit_enforced(self, client: AsyncClient, db: AsyncClient):
        resp = await client.get("/v1/jobs?size=999")  # over max=50
        assert resp.status_code == 422


class TestGetJob:
    async def test_get_existing_job(self, client: AsyncClient, db: AsyncSession):
        company = _make_company()
        db.add(company)
        job = _make_job(company.id)
        db.add(job)
        await db.flush()

        resp = await client.get(f"/v1/jobs/{job.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == str(job.id)

    async def test_get_nonexistent_job_returns_404(self, client: AsyncClient):
        resp = await client.get(f"/v1/jobs/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_get_invalid_uuid_returns_422(self, client: AsyncClient):
        resp = await client.get("/v1/jobs/not-a-uuid")
        assert resp.status_code == 422
