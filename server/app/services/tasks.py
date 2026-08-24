import asyncio
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from app.models.order import Order, OrderItem, Cart, MasterOrder
from app.models.catalog import ProductVariant
from app.db.session import redis_client
from app.db.tenant_context import platform_plane
from app.core.cart_token import GUEST_CART_TTL_SECONDS
from app.services.payments import get_payment_provider

logger = logging.getLogger(__name__)

# Orders that never started a real payment (mock mode, or a checkout that
# was abandoned before ever hitting /pay) still expire quickly -- there's no
# open charge anywhere to worry about racing.
MOCK_ABANDONED_TIMEOUT = timedelta(minutes=15)
# Orders with an open Stripe PaymentIntent get a much longer grace window
# (3DS, a slow bank, a customer who steps away mid-checkout), and are only
# ever expired after that PaymentIntent is explicitly canceled first -- see
# the loop below. Releasing stock while a charge could still land a moment
# later is how you oversell.
STRIPE_ABANDONED_TIMEOUT = timedelta(hours=24)


@platform_plane
async def cleanup_abandoned_checkouts(db: AsyncSession):
    now = datetime.now(timezone.utc)
    # We must replace tzinfo with None if the DB driver doesn't support
    # timezone-aware datetimes.
    mock_cutoff = (now - MOCK_ABANDONED_TIMEOUT).replace(tzinfo=None)
    stripe_cutoff = (now - STRIPE_ABANDONED_TIMEOUT).replace(tzinfo=None)

    # Cast the widest net (the short mock cutoff); orders with an open PI
    # are filtered back out below unless they've *also* passed the much
    # longer stripe cutoff.
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.master_order))
        .where(Order.status == 'pending_payment', Order.created_at <= mock_cutoff)
    )
    candidates = result.scalars().all()

    provider = None
    canceled_master_ids: set[int] = set()
    to_expire: list[Order] = []

    for order in candidates:
        payment_intent_id = order.payment_intent_id
        if not payment_intent_id and order.master_order_id and order.master_order:
            payment_intent_id = order.master_order.payment_intent_id

        if not payment_intent_id:
            # No open charge anywhere for this order -- mock-mode timeout
            # already applies by virtue of the query above.
            to_expire.append(order)
            continue

        if order.created_at > stripe_cutoff:
            continue  # within its (much longer) real-gateway grace window

        master_id = order.master_order_id
        if master_id is None or master_id not in canceled_master_ids:
            provider = provider or get_payment_provider()
            try:
                await provider.cancel_payment_intent(payment_intent_id)
            except Exception:
                # Couldn't confirm the charge is dead -- do NOT release stock
                # under it. Try again next sweep.
                logger.exception(
                    "failed to cancel payment_intent %s while expiring order %s; leaving pending_payment",
                    payment_intent_id, order.id,
                )
                continue
            if master_id is not None:
                canceled_master_ids.add(master_id)

        to_expire.append(order)

    await _expire_orders(to_expire, db)


async def _expire_orders(orders: list[Order], db: AsyncSession) -> None:
    for order in orders:
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

    if orders:
        await db.commit()

@platform_plane
async def cleanup_expired_guest_carts(db: AsyncSession):
    # A guest cart's capability token embeds the same TTL, so an expired cart
    # is one no token could unlock any more -- safe to drop. Claimed carts
    # (user_id set) are excluded; those live until checkout, not by TTL.
    cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=GUEST_CART_TTL_SECONDS)

    result = await db.execute(
        select(Cart).where(
            Cart.user_id.is_(None),
            Cart.created_at <= cutoff_time.replace(tzinfo=None)
        )
    )
    expired_carts = result.scalars().all()
    for cart in expired_carts:
        await db.delete(cart)

    await db.commit()
