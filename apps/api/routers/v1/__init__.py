"""Router v1 — aggregates all sub-routers under /v1 prefix."""

from fastapi import APIRouter

from routers.v1.auth import router as auth_router
from routers.v1.jobs import router as jobs_router

router = APIRouter()

# ── Health ping ───────────────────────────────────────────────────────────────
@router.get("/ping", tags=["health"])
async def ping() -> dict:
    return {"pong": True}


# ── Phase B ───────────────────────────────────────────────────────────────────
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(jobs_router, prefix="/jobs", tags=["jobs"])

from routers.v1.search import router as search_router
router.include_router(search_router)

from routers.v1.saved_jobs import router as saved_jobs_router
from routers.v1.alerts import router as alerts_router
router.include_router(saved_jobs_router)
router.include_router(alerts_router)

# ── Phase F ───────────────────────────────────────────────────────────────────
from routers.v1.resume import router as resume_router
from routers.v1.salary import router as salary_router
router.include_router(resume_router)
router.include_router(salary_router)

# from routers.v1.users import router as users_router
# from routers.v1.applications import router as apps_router
# from routers.v1.skills import router as skills_router
# from routers.v1.analytics import router as analytics_router
# from routers.v1.oauth import router as oauth_router
# from routers.v1.ws import router as ws_router
