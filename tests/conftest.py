import pytest
from httpx import AsyncClient, ASGITransport
import asyncio
from typing import AsyncGenerator
import json
import sys
import os

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Dedicated test database, isolated from the dev database (multivendor_dev).
# Must be set *before* `app.main` (and therefore `app.core.config.settings`)
# is imported below, since that's what app/db/session.py's get_db() — used
# by every route the tests hit through the ASGI transport — reads from.
# Without this, conftest's own fixtures would correctly target
# multivendor_test while the app itself kept writing to multivendor_dev.
DATABASE_URL = "mysql+aiomysql://root:rootpassword@127.0.0.1:3306/multivendor_test"
os.environ["DATABASE_URL"] = DATABASE_URL
os.environ["DB_NAME"] = "multivendor_test"

# The AI layout/product assistant must stay deterministic and network-free in
# tests regardless of whatever GEMINI_API_KEY a developer has set in their own
# .env for local use — same principle as the DATABASE_URL override above.
os.environ["GEMINI_API_KEY"] = ""
os.environ["VERIFY_REMOTE_IMAGE_URLS"] = "false"

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'server'))
from app.main import app
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import redis.asyncio as redis
from app.core.security import create_access_token
from app.core.limiter import limiter

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
    transport = ASGITransport(app=app, raise_app_exceptions=False)
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
        {"id": 1, "slug": "tenant-a", "name": "Store A", "plan_id": 1, "status": "active", "show_all_products_in_marketplace": True},
        {"id": 2, "slug": "tenant-b", "name": "Store B", "plan_id": 2, "status": "active", "show_all_products_in_marketplace": False}
    ]

@pytest.fixture
def seed_users():
    # Identity is global now (see db/seed.sql): id 4 is a single account with a
    # 'customer' membership at BOTH tenants -- there is no separate per-tenant
    # customer row anymore. seed_tokens below still exposes "customer_a" /
    # "customer_b" as distinct fixture *keys* for call-site readability, but
    # both resolve to this same global user id.
    return [
        {"id": 1, "email": "superadmin@platform.com", "role": "super_admin"},
        {"id": 2, "email": "admin.store1@platform.com", "role": "user"},
        {"id": 3, "email": "admin.store2@platform.com", "role": "user"},
        {"id": 4, "email": "customer@gmail.com", "role": "user"},
    ]

@pytest.fixture
def seed_memberships():
    return [
        {"user_id": 2, "tenant_id": 1, "role": "tenant_admin"},
        {"user_id": 3, "tenant_id": 2, "role": "tenant_admin"},
        {"user_id": 4, "tenant_id": 1, "role": "customer"},
        {"user_id": 4, "tenant_id": 2, "role": "customer"},
    ]

@pytest.fixture
def seed_tokens():
    return {
        "super_admin": f"Bearer {create_access_token('1', is_super_admin=True)}",
        "tenant_admin_a": f"Bearer {create_access_token('2')}",
        "tenant_admin_b": f"Bearer {create_access_token('3')}",
        # Same global user (id 4) on purpose -- see seed_users above.
        "customer_a": f"Bearer {create_access_token('4')}",
        "customer_b": f"Bearer {create_access_token('4')}",
        "customer": f"Bearer {create_access_token('4')}",
    }

@pytest.fixture
def seed_products():
    return [
        {"id": 1, "tenant_id": 1, "name": "Product A1", "slug": "product-a1", "base_price": 10.00, "is_active": True, "show_in_marketplace": True},
        {"id": 2, "tenant_id": 2, "name": "Product B1", "slug": "product-b1", "base_price": 20.00, "is_active": True, "show_in_marketplace": True},
        {"id": 3, "tenant_id": 2, "name": "Product B2 (store-only)", "slug": "product-b2", "base_price": 15.00, "is_active": True, "show_in_marketplace": False},
    ]

_seed_statements_cache = None
_clear_db_tables_cache = None

def _load_seed_statements():
    global _seed_statements_cache
    if _seed_statements_cache is None:
        seed_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'db', 'seed.sql')
        with open(seed_path, 'r', encoding='utf-8') as f:
            sql = f.read()
        _seed_statements_cache = [s.strip() for s in sql.split(';') if s.strip()]
    return _seed_statements_cache

@pytest.fixture(autouse=True, scope='function')
async def auto_clear_db():
    # Reuses the module-level `engine` (already open for the whole session,
    # same one db_session runs on) instead of opening/closing a brand new
    # engine per test, and parses db/seed.sql once instead of on every test --
    # this fixture runs before EVERY test, so that overhead was multiplying
    # by the full test count. Also DELETE instead of TRUNCATE: seed.sql always
    # inserts explicit primary keys, so nothing here depends on resetting
    # AUTO_INCREMENT counters, and DELETE skips TRUNCATE's per-table file
    # recreation, which is the dominant cost of this fixture in practice.
    from sqlalchemy import text
    global _clear_db_tables_cache

    # slowapi's default in-memory rate-limit storage lives for the whole
    # pytest process and is keyed by client IP via get_remote_address, which
    # is constant across all requests under httpx's ASGITransport in tests.
    # Without this, rate-limit counters accumulate across the full session
    # (in alphabetical test-file order) even though the DB is reset per test
    # below. Reset it here too so every test starts with a clean budget.
    limiter.reset()

    async with engine.begin() as conn:
        await conn.execute(text('SET FOREIGN_KEY_CHECKS=0'))
        if _clear_db_tables_cache is None:
            result = await conn.execute(text('SHOW TABLES'))
            _clear_db_tables_cache = [row[0] for row in result.all()]
        for table in _clear_db_tables_cache:
            await conn.execute(text(f'DELETE FROM {table}'))
        await conn.execute(text('SET FOREIGN_KEY_CHECKS=1'))

    async with engine.begin() as conn:
        await conn.execute(text('SET FOREIGN_KEY_CHECKS=0'))
        for stmt in _load_seed_statements():
            try:
                await conn.execute(text(stmt))
            except Exception as e:
                print(f"[auto_clear_db] seed statement failed: {stmt[:80]}... -> {e}")
        await conn.execute(text('SET FOREIGN_KEY_CHECKS=1'))
