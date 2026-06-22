from fastapi import APIRouter
from schemas.search import SearchRequest, SearchResponse
from services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])

@router.post("", response_model=SearchResponse)
async def search_jobs(req: SearchRequest):
    """Execute a full-text search against Elasticsearch."""
    return await SearchService.search(req)
