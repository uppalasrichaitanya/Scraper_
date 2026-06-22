"""
routers/v1/resume.py — Resume upload, parse status, and profile endpoints.

Endpoints:
  POST /v1/users/resume          — upload PDF/DOCX, fire parse task
  GET  /v1/users/resume/status   — check parse status
  GET  /v1/users/profile         — return structured profile data
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db
from models.user import User, UserProfile
from schemas.resume import ParseStatusResponse, ProfileResponse, ResumeUploadResponse
from services.resume_service import extract_text, normalize_skills, store_resume_file

router = APIRouter(prefix="/v1/users", tags=["resume"])

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


@router.post(
    "/resume",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a resume for parsing",
)
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate file extension
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {ext}. Only PDF and DOCX are accepted.",
        )

    # Read and validate size
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB.",
        )

    # Store the file
    resume_key = store_resume_file(str(user.id), file_bytes, ext)

    # Ensure user has a profile row
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.add(profile)

    profile.resume_s3_key = resume_key
    await db.commit()

    # Fire the async parse task
    # Import here to avoid circular imports with Celery
    try:
        from crawler.tasks.resume_tasks import parse_resume
        parse_resume.delay(str(user.id), resume_key)
    except Exception:
        # If Celery isn't available (e.g., running API standalone),
        # do synchronous parsing as fallback
        import asyncio
        from services.resume_service import parse_resume_with_llm
        from services.embedding_service import embed_text, build_profile_text
        from datetime import datetime, timezone

        resume_text = extract_text(file_bytes, file.filename or "resume.pdf")
        parsed = await parse_resume_with_llm(resume_text)

        skills = normalize_skills(parsed.get("skills", []))
        profile.current_title = parsed.get("current_title")
        profile.years_experience = parsed.get("years_experience")
        profile.skills = skills
        profile.education = parsed.get("education", [])
        profile.experience = parsed.get("experience", [])
        profile.parsed_at = datetime.now(timezone.utc)
        profile.parse_version = 1
        await db.commit()

    return ResumeUploadResponse(resume_key=resume_key)


@router.get(
    "/resume/status",
    response_model=ParseStatusResponse,
    summary="Check resume parse status",
)
async def get_parse_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        return ParseStatusResponse(is_parsed=False)

    return ParseStatusResponse(
        is_parsed=profile.parsed_at is not None,
        parsed_at=profile.parsed_at,
        skills_count=len(profile.skills) if profile.skills else 0,
        current_title=profile.current_title,
    )


@router.get(
    "/profile",
    response_model=ProfileResponse,
    summary="Get structured profile from parsed resume",
)
async def get_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No profile found. Upload a resume first.",
        )

    # Check if embedding exists via raw SQL (vector column not mapped in ORM)
    emb_result = await db.execute(
        text("SELECT embedding IS NOT NULL as has_emb FROM user_profiles WHERE user_id = :uid"),
        {"uid": str(user.id)},
    )
    emb_row = emb_result.mappings().first()
    has_embedding = bool(emb_row and emb_row["has_emb"])

    return ProfileResponse(
        current_title=profile.current_title,
        years_experience=profile.years_experience,
        skills=profile.skills or [],
        education=profile.education or [],
        experience=profile.experience or [],
        resume_s3_key=profile.resume_s3_key,
        parsed_at=profile.parsed_at,
        has_embedding=has_embedding,
    )
