import asyncio
import sys
import os

# Ensure the root is in PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'apps', 'api'))

from core.database import get_db_context
from core.elasticsearch import get_es
from search.es_sync import bulk_index_jobs

async def run_backfill():
    es = get_es()
    async with get_db_context() as db:
        await bulk_index_jobs(db, es)

if __name__ == "__main__":
    asyncio.run(run_backfill())
