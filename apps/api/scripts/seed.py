"""
seed.py — Seed ~100 sample jobs for local development.
Run after alembic upgrade head and seed_skills.py.

  python scripts/seed.py
"""

from __future__ import annotations

import asyncio
import hashlib
import random
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "api"))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings
from models.company import Company, Location
from models.job import Job
from models.skill import Skill, JobSkill

COMPANIES = [
    ("Stripe", "stripe.com"),
    ("Vercel", "vercel.com"),
    ("Linear", "linear.app"),
    ("Figma", "figma.com"),
    ("Notion", "notion.so"),
    ("Supabase", "supabase.com"),
    ("PlanetScale", "planetscale.com"),
    ("Fly.io", "fly.io"),
    ("Railway", "railway.app"),
    ("Turso", "turso.tech"),
]

LOCATIONS = [
    ("Bengaluru, Karnataka", "Bengaluru", "Karnataka", "India"),
    ("Mumbai, Maharashtra", "Mumbai", "Maharashtra", "India"),
    ("Delhi NCR", "Delhi", "Delhi", "India"),
    ("Hyderabad, Telangana", "Hyderabad", "Telangana", "India"),
    ("Pune, Maharashtra", "Pune", "Maharashtra", "India"),
    ("Remote, Worldwide", None, None, None),
]

TITLES = [
    "Senior Backend Engineer", "Frontend Engineer", "Full Stack Developer",
    "DevOps Engineer", "Data Engineer", "ML Engineer",
    "Site Reliability Engineer", "Platform Engineer",
    "Engineering Manager", "Staff Software Engineer",
    "Principal Engineer", "Android Engineer", "iOS Engineer",
    "Security Engineer", "QA Engineer", "Cloud Architect",
]

SOURCES = ["remoteok", "wwr"]


def make_canonical_id(source: str, url: str, title: str) -> str:
    raw = f"{source.lower()}\x00{url.strip().lower()}\x00{title.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def seed() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        from sqlalchemy import select
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        # Companies — upsert by domain to be idempotent
        companies = []
        for name, domain in COMPANIES:
            stmt = pg_insert(Company).values(
                id=uuid.uuid4(), name=name, domain=domain
            ).on_conflict_do_nothing(index_elements=["domain"])
            await db.execute(stmt)
        await db.flush()
        company_rows = list((await db.execute(select(Company))).scalars().all())

        # Locations — upsert by name to be idempotent
        for name, city, state, country in LOCATIONS:
            exists = (await db.execute(select(Location).where(Location.name == name))).scalar_one_or_none()
            if not exists:
                db.add(Location(id=uuid.uuid4(), name=name, city=city, state=state, country=country))
        await db.flush()
        loc_rows = list((await db.execute(select(Location))).scalars().all())

        # Skills — use existing seeded skills
        skill_rows = list((await db.execute(select(Skill))).scalars().all())

        # Jobs — only add if we have fewer than 100
        from sqlalchemy import func
        existing_count = (await db.execute(select(func.count()).select_from(Job))).scalar()
        if existing_count >= 100:
            print(f"[SKIP] {existing_count} jobs already exist, skipping seed.")
            await engine.dispose()
            return

        # Jobs
        jobs_added = 0
        for i in range(100):
            source = random.choice(SOURCES)
            title = random.choice(TITLES)
            company = random.choice(company_rows)
            is_remote = random.random() > 0.4
            loc = random.choice(loc_rows) if not is_remote else None

            url = f"https://example.com/jobs/{source}/{i}"
            cid = make_canonical_id(source, url, title)

            salary_min = random.choice([None, 600_000, 800_000, 1_200_000, 1_500_000])
            salary_max = salary_min + random.randint(200_000, 600_000) if salary_min else None

            job = Job(
                id=uuid.uuid4(),
                canonical_id=cid,
                title=title,
                description=f"We are looking for a talented {title} to join {company.name}. "
                            "You will work on challenging problems at scale.",
                company_id=company.id,
                location_id=loc.id if loc else None,
                is_remote=is_remote,
                salary_min=salary_min,
                salary_max=salary_max,
                currency="INR" if salary_min else None,
                source=source,
                url=url,
                status="active",
                posted_at=datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30)),
            )
            db.add(job)
            await db.flush()

            # Attach 2–5 random skills
            num_skills = random.randint(2, 5)
            chosen = random.sample(skill_rows, min(num_skills, len(skill_rows)))
            for idx, skill in enumerate(chosen):
                db.add(JobSkill(
                    id=uuid.uuid4(),
                    job_id=job.id,
                    skill_id=skill.id,
                    is_required=idx == 0,  # first skill is required
                ))

            jobs_added += 1

        await db.commit()
        print(f"[OK] Seeded {jobs_added} sample jobs.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
