import pytest
from httpx import AsyncClient, ASGITransport
import asyncio
from typing import AsyncGenerator
import json
import sys
import os

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'server'))
from app.main import app
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import redis.asyncio as redis
from app.core.security import create_access_token

# Setup Database connection
DATABASE_URL = "mysql+aiomysql://root:rootpassword@127.0.0.1:3306/multivendor_db"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

# Setup Redis connection
REDIS_URL = "redis://127.0.0.1:6379/0"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

@pytest.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def redis_client():
    r = redis.from_url(REDIS_URL)
    yield r
    await r.close()

@pytest.fixture
def seed_subscription_plans():
    return [
        {"id": 1, "code": "free", "name": "Free Plan", "price_monthly": 0.00, "max_products": 50, "max_storage_mb": 500},
        {"id": 2, "code": "pro", "name": "Pro Plan", "price_monthly": 29.99, "max_products": 1000, "max_storage_mb": 5000},
        {"id": 3, "code": "enterprise", "name": "Enterprise Plan", "price_monthly": 199.99, "max_products": 999999, "max_storage_mb": 50000}
    ]

@pytest.fixture
def seed_tenants():
    return [
        {"id": 1, "slug": "tenant-a", "name": "Store A", "plan_id": 1, "status": "active"},
        {"id": 2, "slug": "tenant-b", "name": "Store B", "plan_id": 2, "status": "active"}
    ]

@pytest.fixture
def seed_users():
    return [
        {"id": 1, "tenant_id": None, "email": "super@admin.com", "role": "super_admin"},
        {"id": 2, "tenant_id": 1, "email": "admin@tenanta.com", "role": "tenant_admin"},
        {"id": 3, "tenant_id": 2, "email": "admin@tenantb.com", "role": "tenant_admin"},
        {"id": 4, "tenant_id": 1, "email": "customer@tenanta.com", "role": "customer"},
        {"id": 5, "tenant_id": 2, "email": "customer@tenantb.com", "role": "customer"}
    ]

@pytest.fixture
def seed_tokens():
    return {
        "super_admin": f"Bearer {create_access_token('1', 'super_admin')}",
        "tenant_admin_a": f"Bearer {create_access_token('2', 'tenant_admin')}",
        "tenant_admin_b": f"Bearer {create_access_token('3', 'tenant_admin')}",
        "customer_a": f"Bearer {create_access_token('4', 'customer')}",
        "customer_b": f"Bearer {create_access_token('5', 'customer')}"
    }

@pytest.fixture
def seed_products():
    return [
        {"id": 1, "tenant_id": 1, "name": "Product A1", "slug": "product-a1", "base_price": 10.00, "is_active": True},
        {"id": 2, "tenant_id": 2, "name": "Product B1", "slug": "product-b1", "base_price": 20.00, "is_active": True}
    ]

@pytest.fixture(autouse=True, scope='function')
async def auto_clear_db():
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text
    import asyncio
    engine = create_async_engine('mysql+aiomysql://root:rootpassword@127.0.0.1:3306/multivendor_db', echo=False)
    async with engine.begin() as conn:
        await conn.execute(text('SET FOREIGN_KEY_CHECKS=0;'))
        
        result = await conn.execute(text('SHOW TABLES'))
        tables = [row[0] for row in result.all()]
        for table in tables:
            await conn.execute(text(f'TRUNCATE TABLE {table}'))
            
        await conn.execute(text('SET FOREIGN_KEY_CHECKS=1;'))

    with open('../db/seed.sql', 'r', encoding='utf-8') as f:
        sql = f.read()
    
    statements = [s.strip() for s in sql.split(';') if s.strip()]
    async with engine.begin() as conn:
        await conn.execute(text('SET FOREIGN_KEY_CHECKS=0;'))
        for stmt in statements:
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass
        await conn.execute(text('SET FOREIGN_KEY_CHECKS=1;'))
    await engine.dispose()
