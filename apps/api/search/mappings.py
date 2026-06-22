JOBS_INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,  # single-node dev; set to 1 in prod
        "analysis": {
            "analyzer": {
                "job_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "stop", "snowball"]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "id":            {"type": "keyword"},
            "title":         {"type": "text", "analyzer": "job_analyzer", "fields": {"keyword": {"type": "keyword"}}},
            "company_name":  {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "location_city": {"type": "keyword"},
            "location_country": {"type": "keyword"},
            "is_remote":     {"type": "boolean"},
            "salary_min":    {"type": "integer"},
            "salary_max":    {"type": "integer"},
            "salary_currency": {"type": "keyword"},
            "job_type":      {"type": "keyword"},  # full_time, contract, etc.
            "experience_level": {"type": "keyword"},
            "skills":        {"type": "keyword"},   # array of skill slugs
            "description_text": {"type": "text", "analyzer": "job_analyzer"},
            "source_name":   {"type": "keyword"},
            "status":        {"type": "keyword"},
            "posted_at":     {"type": "date"},
            "crawled_at":    {"type": "date"},
            "trust_score":   {"type": "float"}
        }
    }
}
