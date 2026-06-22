from core.elasticsearch import get_es, JOBS_INDEX
from schemas.search import SearchRequest, SearchResponse, SearchHit

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
