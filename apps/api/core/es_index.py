from .elasticsearch import get_es, JOBS_INDEX

JOBS_MAPPING = {
    "mappings": {
        "properties": {
            "id":                   {"type": "keyword"},
            "title_normalized":     {
                "type": "text", "analyzer": "english",
                "fields": {"keyword": {"type": "keyword"}}
            },
            "company_name":         {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}}
            },
            "description_raw":      {"type": "text", "analyzer": "english"},
            "location_city":        {"type": "keyword"},
            "source_platform":      {"type": "keyword"},
            "job_type":             {"type": "keyword"},
            "is_remote":            {"type": "boolean"},
            "salary_min":           {"type": "integer"},
            "salary_max":           {"type": "integer"},
            "experience_min_years": {"type": "integer"},
            "experience_max_years": {"type": "integer"},
            "status":               {"type": "keyword"},
            "skill_names":          {"type": "keyword"},
            "first_seen_at":        {"type": "date"},
            "last_seen_at":         {"type": "date"},
            # Phase E — set index=True and add dims when embeddings exist
            "embedding":            {
                "type": "dense_vector", "dims": 1536, "index": False
            },
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "english": {"type": "standard", "stopwords": "_english_"}
            }
        }
    }
}

async def ensure_index():
    """Idempotent — safe to call on every startup."""
    es = get_es()
    exists = await es.indices.exists(index=JOBS_INDEX)
    if not exists:
        await es.indices.create(index=JOBS_INDEX, body=JOBS_MAPPING)
