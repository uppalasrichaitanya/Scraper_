import asyncio, os, sys
sys.path.insert(0, ".")
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text

async def check():
    engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        s = await db.execute(text("SELECT count(*) FROM skills"))
        print("Skills:", s.scalar())
        j = await db.execute(text("SELECT count(*) FROM jobs WHERE status = 'active'"))
        print("Jobs:", j.scalar())
        v = await db.execute(text("SELECT count(*) FROM job_versions"))
        print("Versions:", v.scalar())
    await engine.dispose()

asyncio.run(check())
