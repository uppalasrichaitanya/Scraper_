from elasticsearch import AsyncElasticsearch
from .mappings import JOBS_INDEX_MAPPING

async def create_index_if_missing(es: AsyncElasticsearch, index_name: str = "jobs"):
    exists = await es.indices.exists(index=index_name)
    if not exists:
        await es.indices.create(index=index_name, body=JOBS_INDEX_MAPPING)
        print(f"Created index: {index_name}")
    else:
        print(f"Index already exists: {index_name}")
