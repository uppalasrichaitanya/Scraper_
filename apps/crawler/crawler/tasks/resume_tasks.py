"""
tasks/resume_tasks.py — Async resume parsing via Celery.

Flow:
  1. Read resume file from storage
  2. Extract text (PDF/DOCX)
  3. Parse with LLM (or fallback)
  4. Normalize skills
  5. Generate user embedding
  6. Store everything in user_profiles
"""
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, text

from ..celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="resume.parse_resume", bind=True, max_retries=2, default_retry_delay=60)
def parse_resume(self, user_id: str, resume_key: str):
    """Parse an uploaded resume and store structured data + embedding."""
    asyncio.run(_parse(user_id, resume_key))


async def _parse(user_id: str, resume_key: str):
    from apps.api.core.database import get_db_context
    from apps.api.models.user import UserProfile
    from apps.api.services.resume_service import (
        extract_text,
        normalize_skills,
        parse_resume_with_llm,
    )
    from apps.api.services.embedding_service import embed_text, build_profile_text

    # 1. Read the file
    file_bytes = _read_resume_file(resume_key)
    if not file_bytes:
        logger.error("Could not read resume file: %s", resume_key)
        return

    # 2. Extract text
    filename = Path(resume_key).name
    try:
        resume_text = extract_text(file_bytes, filename)
    except Exception as e:
        logger.error("Text extraction failed for %s: %s", resume_key, e)
        return

    if not resume_text.strip():
        logger.warning("Empty text extracted from resume: %s", resume_key)
        return

    logger.info("Extracted %d chars from resume for user %s", len(resume_text), user_id)

    # 3. Parse with LLM
    parsed = await parse_resume_with_llm(resume_text)

    # 4. Normalize skills
    raw_skills = parsed.get("skills", [])
    skills = normalize_skills(raw_skills)
    logger.info("Extracted %d skills (normalized to %d) for user %s", len(raw_skills), len(skills), user_id)

    # 5. Generate embedding from profile text
    experience = parsed.get("experience", [])
    profile_text = build_profile_text(
        parsed.get("current_title"),
        skills,
        experience,
    )
    embedding = embed_text(profile_text) if profile_text else None

    # 6. Store in user_profiles
    async with get_db_context() as db:
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            profile = UserProfile(user_id=user_id)
            db.add(profile)
            await db.flush()

        profile.current_title = parsed.get("current_title")
        profile.years_experience = parsed.get("years_experience")
        profile.skills = skills
        profile.education = parsed.get("education", [])
        profile.experience = experience
        profile.parsed_at = datetime.now(timezone.utc)
        profile.parse_version = 1

        # Store embedding via raw SQL (vector column not mapped in ORM)
        if embedding:
            embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
            await db.execute(
                text("UPDATE user_profiles SET embedding = :emb WHERE user_id = :uid"),
                {"emb": embedding_str, "uid": user_id},
            )

        await db.commit()
        logger.info("Resume parsed and stored for user %s: title=%s, %d skills",
                     user_id, profile.current_title, len(skills))


def _read_resume_file(resume_key: str) -> bytes | None:
    """Read resume file from local storage or S3."""
    if resume_key.startswith("s3://"):
        # S3 path
        try:
            import boto3
            from apps.api.core.config import settings

            parts = resume_key.replace("s3://", "").split("/", 1)
            bucket, key = parts[0], parts[1]
            s3 = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
            )
            response = s3.get_object(Bucket=bucket, Key=key)
            return response["Body"].read()
        except Exception as e:
            logger.error("S3 read failed for %s: %s", resume_key, e)
            return None
    else:
        # Local file
        path = Path(resume_key)
        if path.exists():
            return path.read_bytes()
        logger.error("Local file not found: %s", resume_key)
        return None
