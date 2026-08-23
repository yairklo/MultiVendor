import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, TenantAwareSession
from app.db.tenant_context import (
    TenantContextRequired,
    TenantIsolationError,
    bind_tenant,
    reset_tenant,
    unscoped,
)
from app.models.catalog import Category, Product
from app.models.user import User


@pytest.mark.asyncio
async def test_get_db_session_is_tenant_aware():
    async with AsyncSessionLocal() as session:
        assert isinstance(session, TenantAwareSession)
        assert isinstance(session, AsyncSession)


@pytest.mark.asyncio
async def test_tenant_scoped_query_without_context_raises():
    async with AsyncSessionLocal() as db:
        with pytest.raises(TenantContextRequired):
            await db.execute(select(Product))


@pytest.mark.asyncio
async def test_global_identity_query_does_not_require_tenant_context():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == 4))
        assert result.scalar_one().email == "customer@gmail.com"


@pytest.mark.asyncio
async def test_bound_tenant_cannot_see_other_store_products():
    async with AsyncSessionLocal() as db:
        token = bind_tenant(1)
        try:
            products = (await db.execute(select(Product))).scalars().all()
            assert products
            assert {p.tenant_id for p in products} == {1}
            assert all(p.slug != "product-b1" for p in products)
        finally:
            reset_tenant(token)


@pytest.mark.asyncio
async def test_unscoped_can_read_every_tenant():
    async with AsyncSessionLocal() as db:
        with unscoped():
            products = (await db.execute(select(Product))).scalars().all()
        tenant_ids = {p.tenant_id for p in products}
        assert {1, 2}.issubset(tenant_ids)


@pytest.mark.asyncio
async def test_insert_stamps_bound_tenant_id():
    async with AsyncSessionLocal() as db:
        token = bind_tenant(1)
        try:
            category = Category(name={"en": "Session Contract"}, slug="session-contract")
            db.add(category)
            await db.flush()
            assert category.tenant_id == 1
            await db.rollback()
        finally:
            reset_tenant(token)


@pytest.mark.asyncio
async def test_insert_for_other_tenant_is_rejected():
    async with AsyncSessionLocal() as db:
        token = bind_tenant(1)
        try:
            db.add(Category(tenant_id=2, name={"en": "Leak"}, slug="session-leak"))
            with pytest.raises(TenantIsolationError):
                await db.flush()
            await db.rollback()
        finally:
            reset_tenant(token)
