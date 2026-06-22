from __future__ import annotations

import logging
from typing import Any

from core.elasticsearch import get_es, JOBS_INDEX
from schemas.search import SearchRequest, SearchResponse, SearchHit

logger = logging.getLogger(__name__)


class SearchService:
    @staticmethod
    async def search(req: SearchRequest) -> SearchResponse:
        es = get_es()
        
        must_clauses = [{"term": {"status": "active"}}]
        
        if req.q:
            must_clauses.append({
                "multi_match": {
                    "query": req.q,
                    "fields": ["title_normalized^3", "company_name^2", "description_raw", "skill_names"],
                    "fuzziness": "AUTO"
                }
            })
            
        if req.location:
            must_clauses.append({"match": {"location_city": req.location}})
            
        if req.is_remote is not None:
            must_clauses.append({"term": {"is_remote": req.is_remote}})
            
        if req.job_type:
            must_clauses.append({"term": {"job_type": req.job_type}})
            
        if req.experience_max is not None:
            must_clauses.append({"range": {"experience_min_years": {"lte": req.experience_max}}})
            
        if req.salary_min is not None:
            must_clauses.append({"range": {"salary_max": {"gte": req.salary_min}}})
            
        if req.skills:
            for skill in req.skills:
                must_clauses.append({"match": {"skill_names": skill}})
                
        query = {
            "bool": {
                "must": must_clauses
            }
        }
        
        res = await es.search(
            index=JOBS_INDEX,
            query=query,
            from_=req.offset,
            size=req.limit,
            sort=[{"_score": "desc"}, {"first_seen_at": "desc"}]
        )
        
        hits = []
        for hit in res["hits"]["hits"]:
            source = hit["_source"]
            hits.append(SearchHit(
                id=source["id"],
                title_normalized=source.get("title_normalized", ""),
                company_name=source.get("company_name", ""),
                location_city=source.get("location_city"),
                source_platform=source.get("source_platform", ""),
                job_type=source.get("job_type"),
                is_remote=source.get("is_remote", False),
                salary_min=source.get("salary_min"),
                salary_max=source.get("salary_max"),
                experience_min_years=source.get("experience_min_years"),
                experience_max_years=source.get("experience_max_years"),
                skill_names=source.get("skill_names", []),
                score=hit["_score"] or 0.0
            ))
            
        return SearchResponse(
            total=res["hits"]["total"]["value"],
            hits=hits,
            limit=req.limit,
            offset=req.offset
        )


# ── Hybrid Search (Phase F) ──────────────────────────────────────────────────

async def hybrid_search(
    q: str,
    filters: dict[str, Any],
    user_embedding: list[float] | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Combine ES keyword search with pgvector semantic search using RRF.
    
    If user_embedding is provided (authenticated user with resume),
    also compute per-job match scores.
    """
    from elasticsearch import AsyncElasticsearch
    from sqlalchemy import text as sa_text
    from core.database import AsyncSessionLocal

    es = get_es()
    k = 60  # RRF constant (standard value)

    # ── 1. ES keyword search ──────────────────────────────────────────────
    es_scores: dict[str, float] = {}
    must_clauses: list[dict] = [{"term": {"status": "active"}}]
    filter_clauses: list[dict] = []

    if q:
        must_clauses.append({
            "multi_match": {
                "query": q,
                "fields": ["title^3", "company_name^2", "description_text", "skills^2"],
                "type": "best_fields",
                "fuzziness": "AUTO",
            }
        })

    for key, value in filters.items():
        if key == "location" and value:
            filter_clauses.append({"term": {"location_city": value}})
        elif key == "is_remote" and value is not None:
            filter_clauses.append({"term": {"is_remote": value}})
        elif key == "skills" and value:
            filter_clauses.append({"terms": {"skills": value}})
        elif key == "salary_min" and value:
            filter_clauses.append({"range": {"salary_min": {"gte": value}}})

    body = {
        "query": {
            "bool": {
                "must": must_clauses,
                "filter": filter_clauses,
            }
        },
        "sort": [{"_score": "desc"}, {"posted_at": "desc"}],
        "size": 50,
        "track_total_hits": True,
    }

    es_result = await es.search(index="jobs", body=body)
    es_hits = es_result["hits"]["hits"]
    total_es = es_result["hits"]["total"]["value"]

    for hit in es_hits:
        job_id = hit["_source"].get("id", hit["_id"])
        es_scores[job_id] = hit["_score"] or 0.0

    # ── 2. Vector similarity search via pgvector ──────────────────────────
    vector_scores: dict[str, float] = {}
    match_scores: dict[str, float] = {}

    async with AsyncSessionLocal() as db:
        if q:
            # Generate query embedding
            try:
                from services.embedding_service import embed_text
                query_embedding = embed_text(q)
                embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

                vec_result = await db.execute(
                    sa_text("""
                        SELECT je.job_id::text, 1 - (je.embedding <=> :query_emb) AS similarity
                        FROM job_embeddings je
                        JOIN jobs j ON j.id = je.job_id
                        WHERE j.status = 'active'
                        ORDER BY je.embedding <=> :query_emb
                        LIMIT 50
                    """),
                    {"query_emb": embedding_str},
                )
                for row in vec_result.mappings():
                    vector_scores[row["job_id"]] = float(row["similarity"])
            except Exception as e:
                logger.warning("Vector search failed (may not have embeddings yet): %s", e)

        # ── 3. User match scores (if authenticated with embedding) ────────
        if user_embedding:
            try:
                user_emb_str = "[" + ",".join(str(v) for v in user_embedding) + "]"
                all_job_ids = list(set(es_scores.keys()) | set(vector_scores.keys()))

                if all_job_ids:
                    # Compute cosine similarity between user embedding and job embeddings
                    match_result = await db.execute(
                        sa_text("""
                            SELECT je.job_id::text, 1 - (je.embedding <=> :user_emb) AS match_score
                            FROM job_embeddings je
                            WHERE je.job_id::text = ANY(:job_ids)
                        """),
                        {"user_emb": user_emb_str, "job_ids": all_job_ids},
                    )
                    for row in match_result.mappings():
                        match_scores[row["job_id"]] = max(0.0, min(1.0, float(row["match_score"])))
            except Exception as e:
                logger.warning("Match scoring failed: %s", e)

    # ── 4. Reciprocal Rank Fusion ─────────────────────────────────────────
    all_ids = set(es_scores.keys()) | set(vector_scores.keys())

    # Build rank lists
    es_ranked = sorted(es_scores.keys(), key=lambda x: es_scores[x], reverse=True)
    vec_ranked = sorted(vector_scores.keys(), key=lambda x: vector_scores[x], reverse=True)

    final_scores: dict[str, float] = {}
    for job_id in all_ids:
        es_rank = (es_ranked.index(job_id) + 1) if job_id in es_scores else 100
        vec_rank = (vec_ranked.index(job_id) + 1) if job_id in vector_scores else 100
        final_scores[job_id] = (1.0 / (k + es_rank)) + (1.0 / (k + vec_rank))

    ranked_ids = sorted(final_scores.keys(), key=lambda x: final_scores[x], reverse=True)

    # Paginate
    start = (page - 1) * page_size
    page_ids = ranked_ids[start : start + page_size]

    # ── 5. Fetch full job data from ES for the page ───────────────────────
    items = []
    for job_id in page_ids:
        # Find the ES hit data
        es_hit = next((h["_source"] for h in es_hits if h["_source"].get("id") == job_id), None)
        if es_hit:
            item = dict(es_hit)
            item["_rank_score"] = final_scores.get(job_id, 0.0)
            item["match_score"] = match_scores.get(job_id)
            items.append(item)

    return {
        "total": len(all_ids),
        "page": page,
        "page_size": page_size,
        "items": items,
        "has_next": len(ranked_ids) > start + page_size,
    }


async def get_user_embedding(user_id: str) -> list[float] | None:
    """Fetch the user's profile embedding from pgvector."""
    from sqlalchemy import text as sa_text
    from core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            sa_text("SELECT embedding::text FROM user_profiles WHERE user_id = :uid AND embedding IS NOT NULL"),
            {"uid": user_id},
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        # Parse the vector string "[0.1,0.2,...]" back to list
        return [float(v) for v in row.strip("[]").split(",")]

