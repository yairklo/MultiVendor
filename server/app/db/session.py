from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import redis.asyncio as redis
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def get_redis():
    yield redis_client
