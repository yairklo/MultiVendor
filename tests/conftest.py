import pytest
from httpx import AsyncClient, ASGITransport
import asyncio
from typing import AsyncGenerator
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from multivendor_fastapi_api_routes_skeleton import app
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import redis.asyncio as redis

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
        "super_admin": "Bearer token_super_admin",
        "tenant_admin_a": "Bearer token_tenant_admin_a",
        "tenant_admin_b": "Bearer token_tenant_admin_b",
        "customer_a": "Bearer token_customer_a",
        "customer_b": "Bearer token_customer_b"
    }

@pytest.fixture
def seed_products():
    return [
        {"id": 1, "tenant_id": 1, "name": "Product A1", "slug": "product-a1", "base_price": 10.00, "is_active": True},
        {"id": 2, "tenant_id": 2, "name": "Product B1", "slug": "product-b1", "base_price": 20.00, "is_active": True}
    ]
