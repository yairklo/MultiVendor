import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from uuid import UUID
from collections import defaultdict
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import redis_client
from app.models.tenant import Tenant
from app.models.catalog import ProductVariant, Product
from app.models.order import MarketplaceCartItem, MasterOrder, Order, OrderItem
from app.models.user import UserStoreMembership
from app.schemas.marketplace_schemas import (
    MarketplaceAddToCartRequest, MarketplaceCartResponse, MarketplaceCartItemResponse,
    MarketplaceCheckoutRequest, MasterOrderResponse,
)
from app.schemas.order_schemas import OrderResponse, OrderItemResponse

# Flat platform cut of each vendor's sub-order subtotal. A fixed constant
# rather than a per-tenant/per-plan rate table -- good enough for the MVP
# split; making it configurable per tenant is a natural next step, not
# something the marketplace checkout path needs to block on.
PLATFORM_COMMISSION_RATE = Decimal("0.10")


def _resolve_product_name(name) -> str:
    if isinstance(name, dict):
        return name.get('en') or next(iter(name.values()), '')
    return str(name)


def _round2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def add_to_marketplace_cart_service(cart_id: UUID, req: MarketplaceAddToCartRequest, db: AsyncSession):
    variant_result = await db.execute(
        select(ProductVariant)
        .join(Product)
        .where(
            ProductVariant.id == req.variant_id,
            Product.is_active == True,
        )
    )
    variant = variant_result.scalar_one_or_none()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found or product inactive")

    if variant.stock_quantity < req.quantity:
        raise HTTPException(status_code=400, detail="Not enough stock")

    item_result = await db.execute(
        select(MarketplaceCartItem).where(
            MarketplaceCartItem.cart_id == str(cart_id),
            MarketplaceCartItem.variant_id == req.variant_id,
        )
    )
    item = item_result.scalar_one_or_none()

    if item:
        item.quantity += req.quantity
    else:
        item = MarketplaceCartItem(
            cart_id=str(cart_id),
            tenant_id=variant.tenant_id,
            variant_id=req.variant_id,
            quantity=req.quantity,
        )
        db.add(item)

    await db.commit()
    return {"status": "ok"}


async def get_marketplace_cart_service(cart_id: UUID, db: AsyncSession) -> MarketplaceCartResponse:
    result = await db.execute(
        select(MarketplaceCartItem, Tenant)
        .join(Tenant, Tenant.id == MarketplaceCartItem.tenant_id)
        .where(MarketplaceCartItem.cart_id == str(cart_id))
        .options(
            selectinload(MarketplaceCartItem.variant).selectinload(ProductVariant.product).selectinload(Product.images)
        )
    )
    rows = result.all()

    items = []
    subtotal = Decimal("0.00")
    tenant_ids = set()
    for cart_item, tenant in rows:
        variant = cart_item.variant
        product = variant.product
        unit_price = variant.price_override if variant.price_override is not None else product.base_price
        total_price = unit_price * cart_item.quantity
        subtotal += total_price
        tenant_ids.add(tenant.id)

        image_url = next((img.image_url for img in product.images if img.is_primary), None)
        if not image_url and product.images:
            image_url = product.images[0].image_url

        items.append(MarketplaceCartItemResponse(
            id=cart_item.id,
            tenant_id=tenant.id,
            tenant_slug=tenant.slug,
            tenant_name=tenant.name,
            variant_id=variant.id,
            product_name=_resolve_product_name(product.name),
            sku=variant.sku,
            unit_price=unit_price,
            quantity=cart_item.quantity,
            total_price=total_price,
            image_url=image_url,
        ))

    return MarketplaceCartResponse(
        cart_id=cart_id, items=items, subtotal=subtotal, vendor_count=len(tenant_ids)
    )


async def remove_from_marketplace_cart_service(cart_id: UUID, item_id: int, db: AsyncSession):
    item_result = await db.execute(
        select(MarketplaceCartItem).where(MarketplaceCartItem.cart_id == str(cart_id), MarketplaceCartItem.id == item_id)
    )
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    await db.delete(item)
    await db.commit()
    return {"status": "ok"}


async def update_marketplace_cart_item_service(cart_id: UUID, item_id: int, quantity: int, db: AsyncSession):
    item_result = await db.execute(
        select(MarketplaceCartItem).where(MarketplaceCartItem.cart_id == str(cart_id), MarketplaceCartItem.id == item_id)
    )
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    variant_result = await db.execute(select(ProductVariant).where(ProductVariant.id == item.variant_id))
    variant = variant_result.scalar_one_or_none()
    if variant and variant.stock_quantity < quantity:
        raise HTTPException(status_code=400, detail="Not enough stock")

    item.quantity = quantity
    await db.commit()
    return {"status": "ok"}


def _order_to_response(order: Order, items: list[OrderItem]) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        tenant_id=order.tenant_id,
        customer_id=order.user_id,
        order_number=order.order_number,
        subtotal=order.subtotal,
        discount_amt=order.discount_amt,
        shipping_method_id=order.shipping_method_id,
        shipping_fee=order.shipping_fee,
        total_amount=order.total_amount,
        status=order.status,
        order_type=order.order_type,
        shipping_info=order.shipping_json or {},
        created_at=order.created_at,
        items=[OrderItemResponse(
            id=i.id, variant_id=i.variant_id, product_name=i.product_name,
            sku=i.sku, unit_price=i.unit_price, quantity=i.quantity,
        ) for i in items],
    )


async def get_master_order_service(master_order_id: int, user_id: int, db: AsyncSession) -> MasterOrderResponse:
    master_result = await db.execute(
        select(MasterOrder).where(MasterOrder.id == master_order_id, MasterOrder.user_id == user_id)
    )
    master_order = master_result.scalar_one_or_none()
    if not master_order:
        raise HTTPException(status_code=404, detail="Order not found")

    orders_result = await db.execute(
        select(Order).where(Order.master_order_id == master_order_id).options(selectinload(Order.items))
    )
    sub_orders = orders_result.scalars().all()

    return MasterOrderResponse(
        id=master_order.id,
        master_order_number=master_order.master_order_number,
        total_amount=master_order.total_amount,
        created_at=master_order.created_at,
        sub_orders=[_order_to_response(order, order.items) for order in sub_orders],
    )


async def pay_master_order_service(master_order_id: int, user_id: int, db: AsyncSession) -> MasterOrderResponse:
    # Mock payment gateway, same as the single-store pay_order_service -- but
    # pays every vendor's sub-order under this master order in one call/one
    # commit, rather than making the frontend loop N separate pay requests
    # (which could fail partway through and leave some vendors paid and
    # others not, for what the shopper experienced as a single purchase).
    master_result = await db.execute(
        select(MasterOrder).where(MasterOrder.id == master_order_id, MasterOrder.user_id == user_id)
    )
    master_order = master_result.scalar_one_or_none()
    if not master_order:
        raise HTTPException(status_code=404, detail="Order not found")

    orders_result = await db.execute(
        select(Order).where(Order.master_order_id == master_order_id).options(selectinload(Order.items))
    )
    sub_orders = orders_result.scalars().all()
    if not sub_orders:
        raise HTTPException(status_code=404, detail="Order not found")
    if not any(o.status == 'pending_payment' for o in sub_orders):
        raise HTTPException(status_code=400, detail="Order is not awaiting payment")

    for order in sub_orders:
        if order.status == 'pending_payment':
            order.status = 'processing'
    await db.commit()

    return MasterOrderResponse(
        id=master_order.id,
        master_order_number=master_order.master_order_number,
        total_amount=master_order.total_amount,
        created_at=master_order.created_at,
        sub_orders=[_order_to_response(order, order.items) for order in sub_orders],
    )


async def marketplace_checkout_service(req: MarketplaceCheckoutRequest, user_id: int, db: AsyncSession) -> MasterOrderResponse:
    cart_id = str(req.cart_id)
    result = await db.execute(
        select(MarketplaceCartItem)
        .where(MarketplaceCartItem.cart_id == cart_id)
        .options(selectinload(MarketplaceCartItem.variant).selectinload(ProductVariant.product))
    )
    cart_items = result.scalars().all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="Marketplace cart is empty or not found")

    # Group by vendor: this is the actual "order splitting" -- one sub-order
    # per tenant_id, all children of a single master order below.
    by_tenant: dict[int, list[MarketplaceCartItem]] = defaultdict(list)
    for item in cart_items:
        by_tenant[item.tenant_id].append(item)

    needs_shipping_address = any(
        item.variant.product.product_type != 'digital'
        for items in by_tenant.values() for item in items
    )
    if needs_shipping_address and not req.shipping_address:
        raise HTTPException(status_code=400, detail="Shipping address is required for physical goods")

    # Sort (tenant_id, variant_id) locking order across ALL vendors so two
    # concurrent marketplace checkouts can never deadlock against each other,
    # same principle as the single-store checkout_service.
    lock_targets = sorted({
        (tenant_id, item.variant_id)
        for tenant_id, items in by_tenant.items() for item in items
    })

    locks = []
    try:
        for tenant_id, variant_id in lock_targets:
            lock_key = f"lock:tenant:{tenant_id}:variant:{variant_id}"
            lock = redis_client.lock(lock_key, timeout=10)
            acquired = await lock.acquire(blocking=False)
            if not acquired:
                raise HTTPException(status_code=409, detail=f"Variant {variant_id} is currently being checked out by someone else")
            locks.append(lock)

        # Pass 1: validate stock and compute each vendor's subtotal before
        # writing anything, so a failure for one vendor doesn't leave a
        # half-built master order behind.
        per_tenant_subtotal: dict[int, Decimal] = {}
        per_tenant_items: dict[int, list[dict]] = {}
        per_tenant_is_digital: dict[int, bool] = {}

        for tenant_id, items in by_tenant.items():
            consolidated: dict[int, int] = defaultdict(int)
            for item in items:
                consolidated[item.variant_id] += item.quantity

            subtotal = Decimal("0.00")
            order_items_data = []
            is_entirely_digital = True
            for item in items:
                variant = item.variant
                product = variant.product
                if product.product_type != 'digital':
                    is_entirely_digital = False
                unit_price = variant.price_override if variant.price_override is not None else product.base_price
                subtotal += unit_price * item.quantity
                order_items_data.append({
                    "variant_id": variant.id,
                    "product_name": _resolve_product_name(product.name),
                    "sku": variant.sku,
                    "unit_price": unit_price,
                    "quantity": item.quantity,
                })

            for variant_id, qty in consolidated.items():
                variant_result = await db.execute(select(ProductVariant).where(ProductVariant.id == variant_id))
                variant = variant_result.scalar_one()
                if variant.stock_quantity < qty:
                    raise HTTPException(status_code=400, detail=f"Not enough stock for variant {variant_id}")

            per_tenant_subtotal[tenant_id] = subtotal
            per_tenant_items[tenant_id] = order_items_data
            per_tenant_is_digital[tenant_id] = is_entirely_digital

        # Pass 2: deduct stock now that every vendor group has passed validation.
        for tenant_id, items in by_tenant.items():
            consolidated: dict[int, int] = defaultdict(int)
            for item in items:
                consolidated[item.variant_id] += item.quantity
            for variant_id, qty in consolidated.items():
                variant_result = await db.execute(select(ProductVariant).where(ProductVariant.id == variant_id))
                variant = variant_result.scalar_one()
                variant.stock_quantity -= qty

        total_amount = sum(per_tenant_subtotal.values(), Decimal("0.00"))

        master_order = MasterOrder(
            user_id=user_id,
            master_order_number=f"MORD-{uuid.uuid4().hex[:8].upper()}",
            total_amount=total_amount,
        )
        db.add(master_order)
        await db.flush()

        sub_orders = []
        for tenant_id, subtotal in per_tenant_subtotal.items():
            # Same auto-provisioning as a direct storefront visit (see
            # deps.get_tenant_customer) -- a marketplace purchase from a
            # vendor a user has never bought from before should still make
            # them show up in that vendor's customer list.
            membership_result = await db.execute(
                select(UserStoreMembership).where(
                    UserStoreMembership.user_id == user_id, UserStoreMembership.tenant_id == tenant_id
                )
            )
            if not membership_result.scalar_one_or_none():
                db.add(UserStoreMembership(user_id=user_id, tenant_id=tenant_id, role='customer'))

            platform_commission = _round2(subtotal * PLATFORM_COMMISSION_RATE)
            vendor_net_payout = subtotal - platform_commission
            is_digital = per_tenant_is_digital[tenant_id]

            order = Order(
                tenant_id=tenant_id,
                user_id=user_id,
                master_order_id=master_order.id,
                order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
                subtotal=subtotal,
                discount_amt=Decimal("0.00"),
                shipping_fee=Decimal("0.00"),
                total_amount=subtotal,
                platform_commission=platform_commission,
                vendor_net_payout=vendor_net_payout,
                status='pending_payment',
                order_type='digital' if is_digital else 'physical',
                shipping_json=req.shipping_address if not is_digital else None,
            )
            db.add(order)
            await db.flush()

            for data in per_tenant_items[tenant_id]:
                db.add(OrderItem(
                    tenant_id=tenant_id,
                    order_id=order.id,
                    variant_id=data["variant_id"],
                    product_name=data["product_name"],
                    sku=data["sku"],
                    unit_price=data["unit_price"],
                    quantity=data["quantity"],
                ))
            sub_orders.append(order)

        for item in cart_items:
            await db.delete(item)

        await db.commit()
        await db.refresh(master_order)

        response_sub_orders = []
        for order in sub_orders:
            await db.refresh(order)
            items_result = await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))
            response_sub_orders.append(_order_to_response(order, items_result.scalars().all()))

        return MasterOrderResponse(
            id=master_order.id,
            master_order_number=master_order.master_order_number,
            total_amount=master_order.total_amount,
            created_at=master_order.created_at,
            sub_orders=response_sub_orders,
        )
    finally:
        for lock in locks:
            try:
                await lock.release()
            except Exception:
                pass
