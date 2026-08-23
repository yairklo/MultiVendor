import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.order import Order, OrderItem
from app.models.catalog import ProductVariant
from app.db.session import redis_client
from app.db.tenant_context import platform_plane

@platform_plane
async def cleanup_abandoned_checkouts(db: AsyncSession):
    # Find orders in pending_payment older than 15 minutes
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=15)
    
    # We must replace tzinfo to None if the DB driver doesn't support timezone-aware datetimes
    result = await db.execute(
        select(Order).where(
            Order.status == 'pending_payment',
            Order.created_at <= cutoff_time.replace(tzinfo=None)
        )
    )
    abandoned_orders = result.scalars().all()
    
    for order in abandoned_orders:
        order.status = 'expired'
        
        # Release the lock
        lock_key = f"lock:order:{order.id}"
        await redis_client.delete(lock_key)
        
        # Restore stock
        items_res = await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))
        items = items_res.scalars().all()
        for item in items:
            if item.variant_id:
                variant_res = await db.execute(select(ProductVariant).where(ProductVariant.id == item.variant_id))
                variant = variant_res.scalar_one_or_none()
                if variant:
                    variant.stock_quantity += item.quantity
                    
    await db.commit()
