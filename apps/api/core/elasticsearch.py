from elasticsearch import AsyncElasticsearch
from .config import settings

_client: AsyncElasticsearch | None = None

def get_es() -> AsyncElasticsearch:
    global _client
    if _client is None:
        _client = AsyncElasticsearch(
            hosts=[settings.ELASTICSEARCH_URL],
            request_timeout=10,
            retry_on_timeout=True,
            max_retries=2,
        )
    return _client

async def close_es():
    global _client
    if _client:
        await _client.close()
        _client = None

JOBS_INDEX = "jobs_v1"
