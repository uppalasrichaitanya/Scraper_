"""
Crawler adapter and pipeline tests.

Run with: pytest apps/crawler/tests/ -v
"""
import json
import pathlib

import pytest

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


# ── RemoteOK adapter ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_remoteok_field_coverage():
    from crawler.adapters.remoteok import RemoteOKAdapter

    html = (FIXTURES / "remoteok_sample.json").read_text()
    adapter = RemoteOKAdapter()
    jobs = await adapter.parse_job(html, "https://remoteok.com/api")

    assert len(jobs) > 0, "Expected at least one job"

    required_fields = ["title", "company_name", "source_url"]
    coverage = sum(
        1 for job in jobs if all(getattr(job, f) for f in required_fields)
    ) / len(jobs)
    assert coverage >= 0.95, f"Field coverage {coverage:.0%} below 95%"


@pytest.mark.asyncio
async def test_remoteok_salary_extraction():
    from crawler.adapters.remoteok import RemoteOKAdapter

    html = (FIXTURES / "remoteok_sample.json").read_text()
    adapter = RemoteOKAdapter()
    jobs = await adapter.parse_job(html, "https://remoteok.com/api")

    # First two jobs in fixture have salary data
    jobs_with_salary = [j for j in jobs if j.salary_raw]
    assert len(jobs_with_salary) >= 2, "Expected salary data on at least 2 jobs"
    assert "$80000" in jobs_with_salary[0].salary_raw or "$80k" in jobs_with_salary[0].salary_raw.lower() or "80000" in jobs_with_salary[0].salary_raw


@pytest.mark.asyncio
async def test_remoteok_skips_metadata_entry():
    """First element of RemoteOK API response is metadata — must be skipped."""
    from crawler.adapters.remoteok import RemoteOKAdapter

    # Metadata entry has no 'position' key
    payload = json.dumps([{"legal": "..."}])
    adapter = RemoteOKAdapter()
    jobs = await adapter.parse_job(payload, "https://remoteok.com/api")
    assert jobs == []


# ── WWR adapter ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_wwr_field_coverage():
    from crawler.adapters.wwr import WWRAdapter

    html = (FIXTURES / "wwr_sample.xml").read_text()
    adapter = WWRAdapter()
    jobs = await adapter.parse_job(html, "https://weworkremotely.com/remote-jobs.rss")

    assert len(jobs) == 3
    for job in jobs:
        assert job.title, "title must not be empty"
        assert job.company_name, "company_name must not be empty"
        assert job.source_url, "source_url must not be empty"
        assert job.is_remote is True


@pytest.mark.asyncio
async def test_wwr_splits_title_at_company():
    """WWR entries have 'Title at Company' format — must be split correctly."""
    from crawler.adapters.wwr import WWRAdapter

    html = (FIXTURES / "wwr_sample.xml").read_text()
    adapter = WWRAdapter()
    jobs = await adapter.parse_job(html, "https://weworkremotely.com/remote-jobs.rss")

    assert jobs[0].title == "Full-Stack Engineer"
    assert jobs[0].company_name == "Basecamp"
    assert jobs[1].title == "Senior Backend Developer"
    assert jobs[1].company_name == "Shopify"


# ── Salary parser ─────────────────────────────────────────────────────────────

def test_salary_parser_cases():
    from crawler.pipeline.salary_parser import parse_salary

    cases = [
        ("12-18 LPA", 1_200_000, 1_800_000),
        ("15 lakh", 1_500_000, 1_500_000),
        ("Not disclosed", None, None),
        (None, None, None),
        ("", None, None),
    ]
    for raw, exp_min, exp_max in cases:
        lo, hi = parse_salary(raw)
        assert lo == exp_min and hi == exp_max, (
            f"Failed for '{raw}': expected ({exp_min}, {exp_max}), got ({lo}, {hi})"
        )


def test_salary_parser_monthly():
    from crawler.pipeline.salary_parser import parse_salary

    # ₹50,000/month → 600,000/year
    lo, hi = parse_salary("₹50,000/month")
    assert lo == 600_000 and hi == 600_000, f"Monthly parse failed: ({lo}, {hi})"


def test_salary_parser_usd():
    from crawler.pipeline.salary_parser import parse_salary

    # $80k-$120k at ₹83/$ = 6,640,000 – 9,960,000
    lo, hi = parse_salary("$80k-$120k")
    assert lo == 6_640_000 and hi == 9_960_000, f"USD parse failed: ({lo}, {hi})"


# ── Deduplicator ──────────────────────────────────────────────────────────────

def test_canonical_id_dedup():
    from crawler.pipeline.deduplicator import compute_canonical_id

    # Same job from two different sources → same canonical_id
    id1 = compute_canonical_id("Senior Software Engineer", "Google", "Bangalore")
    id2 = compute_canonical_id("Sr. Software Engineer", "Google", "Bangalore")
    assert id1 == id2, "sr → senior alias normalisation failed"


def test_canonical_id_different_companies():
    from crawler.pipeline.deduplicator import compute_canonical_id

    id1 = compute_canonical_id("Software Engineer", "Google", "Bangalore")
    id2 = compute_canonical_id("Software Engineer", "Microsoft", "Bangalore")
    assert id1 != id2


def test_canonical_id_sde_alias():
    from crawler.pipeline.deduplicator import compute_canonical_id

    id1 = compute_canonical_id("SDE II", "Amazon", "Hyderabad")
    id2 = compute_canonical_id("Software Engineer II", "Amazon", "Hyderabad")
    assert id1 == id2, "sde → software engineer alias failed"


# ── Normalizer ────────────────────────────────────────────────────────────────

def test_normalizer_end_to_end():
    from crawler.pipeline.normalizer import normalize
    from crawler.schemas.raw_job import RawJobSchema

    raw = RawJobSchema(
        source_platform="remoteok",
        source_url="https://remoteok.com/jobs/1",
        title="Senior Python Developer",
        company_name="Acme Corp",
        location_raw="Bangalore, India",
        description_raw="We need 5-8 years of Python experience.",
        salary_raw="20-30 LPA",
        skills_raw=["python", "django"],
        is_remote=False,
    )
    result = normalize(raw)

    assert result.canonical_id, "canonical_id must not be empty"
    assert result.title_normalized == "senior python developer"
    assert result.salary_min == 2_000_000
    assert result.salary_max == 3_000_000
    assert result.location_city == "Bangalore"
    assert result.experience_min_years == 5
    assert result.experience_max_years == 8


def test_normalizer_remote_detection():
    from crawler.pipeline.normalizer import normalize
    from crawler.schemas.raw_job import RawJobSchema

    raw = RawJobSchema(
        source_platform="remoteok",
        source_url="https://remoteok.com/jobs/2",
        title="Remote Backend Engineer",
        company_name="Startup Inc",
        is_remote=False,  # source doesn't set it, but title has "Remote"
    )
    result = normalize(raw)
    assert result.is_remote is True
