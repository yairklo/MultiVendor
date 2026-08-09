import pytest
from httpx import AsyncClient
import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.models.order import Order, OrderItem
from app.models.catalog import ProductVariant
from app.services.tasks import cleanup_abandoned_checkouts
from app.db.session import redis_client

@pytest.mark.asyncio
async def test_cleanup_abandoned_checkouts(db_session):
    # Seed a 20-minute-old pending_payment order
    old_time = datetime.now(timezone.utc) - timedelta(minutes=20)
    
    order = Order(
        tenant_id=1,
        user_id=4,
        order_number="ORD-TEST-1",
        subtotal=10.0,
        total_amount=10.0,
        status="pending_payment",
        created_at=old_time.replace(tzinfo=None) # naive datetime for mysql
    )
    db_session.add(order)
    await db_session.flush()

    order_item = OrderItem(
        tenant_id=1,
        order_id=order.id,
        variant_id=1,
        product_name="Product A1",
        sku="product-a1",
        unit_price=10.0,
        quantity=2
    )
    db_session.add(order_item)

    # Initial stock
    variant_res = await db_session.execute(select(ProductVariant).where(ProductVariant.id == 1))
    variant = variant_res.scalar_one()
    initial_stock = variant.stock_quantity

    # Seed a redis lock for this order
    lock_key = f"lock:order:{order.id}"
    await redis_client.set(lock_key, "locked", ex=3600)

    await db_session.commit()

    # Run cleanup
    await cleanup_abandoned_checkouts(db_session)

    # Assert order is expired
    order_res = await db_session.execute(select(Order).where(Order.id == order.id))
    updated_order = order_res.scalar_one()
    assert updated_order.status == "expired"

    # Assert stock is restored
    variant_res = await db_session.execute(select(ProductVariant).where(ProductVariant.id == 1))
    updated_variant = variant_res.scalar_one()
    assert updated_variant.stock_quantity == initial_stock + 2

    # Assert redis lock is cleared
    lock_exists = await redis_client.exists(lock_key)
    assert not lock_exists

@pytest.mark.asyncio
async def test_rate_limiting_and_error_handling(async_client: AsyncClient):
    # Test Rate Limiting on /auth/login
    for _ in range(10):
        res = await async_client.post("/api/v1/auth/login", json={"email": "customer@tenanta.com", "password": "password"})
        # might be 400 or 401, but not 429 yet
        assert res.status_code != 429
    
    res = await async_client.post("/api/v1/auth/login", json={"email": "customer@tenanta.com", "password": "password"})
    assert res.status_code == 429
    
    # Test Global Error Handling
    # We will trigger a 500 error on health or some route if possible, or create a mock route in the test
    res = await async_client.get("/health/error_test")
    assert res.status_code == 500
    data = res.json()
    assert data["detail"] == "An internal server error occurred."
    assert data["code"] == "INTERNAL_ERROR"

@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient):
    res = await async_client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["redis"] == "connected"
