import logging
import math
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
from app.core.config import settings
from app.models.tenant import Tenant
from app.models.order import Order, OrderItem, MasterOrder
from app.models.user import User, UserStoreMembership
from app.models.catalog import ProductVariant, Product, ProductBundleItem
from app.schemas.order_schemas import PaginatedOrderResponse, OrderResponse, OrderItemResponse, PaymentIntentInfo
from app.schemas.auth_schemas import CustomerSummaryResponse
from app.db.tenant_context import platform_plane
from app.services.payments import get_payment_provider, get_or_create_payment_intent
from app.services.payments.base import amount_matches

logger = logging.getLogger(__name__)

PAID_ORDER_STATUSES = ('processing', 'completed')

def _order_to_response(order: Order, customer: User | None = None, tenant_slug: str | None = None) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        tenant_id=order.tenant_id,
        tenant_slug=tenant_slug,
        customer_id=order.user_id,
        customer_name=customer.full_name if customer else None,
        customer_email=customer.email if customer else None,
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
            id=i.id,
            variant_id=i.variant_id,
            product_name=i.product_name,
            sku=i.sku,
            unit_price=i.unit_price,
            quantity=i.quantity
        ) for i in order.items]
    )

async def list_tenant_orders_service(
    tenant_slug: str, db: AsyncSession,
    status: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    customer_email: str | None = None,
    limit: int | None = None,
) -> list[OrderResponse]:
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")

    query = (
        select(Order, User)
        .join(User, User.id == Order.user_id)
        .where(Order.tenant_id == tenant_id)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
    )
    if status:
        query = query.where(Order.status == status)
    if start_date:
        query = query.where(Order.created_at >= start_date)
    if end_date:
        query = query.where(Order.created_at <= end_date)
    if customer_email:
        query = query.where(User.email == customer_email)
    if limit:
        query = query.limit(limit)

    result = await db.execute(query)
    return [_order_to_response(order, customer) for order, customer in result.all()]

async def get_tenant_order_service(tenant_slug: str, order_id: int, db: AsyncSession) -> OrderResponse:
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")

    result = await db.execute(
        select(Order, User)
        .join(User, User.id == Order.user_id)
        .where(Order.tenant_id == tenant_id, Order.id == order_id)
        .options(selectinload(Order.items))
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    order, customer = row
    return _order_to_response(order, customer)

async def list_tenant_customers_service(tenant_slug: str, db: AsyncSession) -> list[CustomerSummaryResponse]:
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")

    paid_amount = case((Order.status.in_(PAID_ORDER_STATUSES), Order.total_amount), else_=0)
    result = await db.execute(
        select(
            User,
            func.count(Order.id).label('orders_count'),
            func.coalesce(func.sum(paid_amount), 0).label('total_spent'),
            func.max(Order.created_at).label('last_order_at'),
        )
        .join(UserStoreMembership, (UserStoreMembership.user_id == User.id) & (UserStoreMembership.tenant_id == tenant_id))
        .outerjoin(Order, (Order.user_id == User.id) & (Order.tenant_id == tenant_id))
        .where(UserStoreMembership.role == 'customer', UserStoreMembership.is_active == True)
        .group_by(User.id)
        .order_by(User.created_at.desc())
    )

    return [
        CustomerSummaryResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            created_at=user.created_at,
            orders_count=orders_count,
            total_spent=float(total_spent),
            last_order_at=last_order_at,
        )
        for user, orders_count, total_spent, last_order_at in result.all()
    ]

async def restore_stock_for_order(order: Order, db: AsyncSession):
    # Determine variants to restore
    for item in order.items:
        variant_result = await db.execute(select(ProductVariant).options(selectinload(ProductVariant.product)).where(ProductVariant.id == item.variant_id))
        variant = variant_result.scalar_one_or_none()
        
        if not variant:
            continue
            
        if variant.product.is_bundle:
            bundle_res = await db.execute(select(ProductBundleItem).where(ProductBundleItem.bundle_product_id == variant.product_id))
            components = bundle_res.scalars().all()
            for comp in components:
                comp_var_res = await db.execute(select(ProductVariant).where(ProductVariant.id == comp.component_variant_id))
                comp_var = comp_var_res.scalar_one_or_none()
                if comp_var:
                    comp_var.stock_quantity += (item.quantity * comp.quantity)
        else:
            variant.stock_quantity += item.quantity


async def update_order_status_service(tenant_slug: str, order_id: int, status: str, db: AsyncSession):
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")

    order_result = await db.execute(select(Order).options(selectinload(Order.items)).where(Order.id == order_id, Order.tenant_id == tenant_id))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # 'pending' is deliberately excluded: checkout always creates orders as
    # 'pending_payment', which becomes 'processing' once paid — plain 'pending'
    # is a legacy status no real order flow ever produces or should be set to.
    valid_statuses = ['processing', 'completed', 'cancelled']
    if status not in valid_statuses:
        raise HTTPException(status_code=422, detail="Invalid status transition")

    # If transitioning to cancelled, restore stock
    if status == 'cancelled' and order.status != 'cancelled':
        await restore_stock_for_order(order, db)

    order.status = status
    await db.commit()
    return {"status": "ok", "order_status": order.status}

@platform_plane
async def list_customer_orders_service(
    user_id: int, page: int, page_size: int, db: AsyncSession, tenant_slug: str | None = None
) -> PaginatedOrderResponse:
    query = select(Order).where(Order.user_id == user_id)
    if tenant_slug:
        tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
        tenant_id = tenant_result.scalar_one_or_none()
        if not tenant_id:
            raise HTTPException(status_code=404, detail="Tenant not found")
        query = query.where(Order.tenant_id == tenant_id)

    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar_one()
    
    query = query.options(selectinload(Order.items))
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    orders = result.scalars().all()

    tenant_ids = {order.tenant_id for order in orders}
    slug_by_id: dict[int, str] = {}
    if tenant_ids:
        tenants = await db.execute(select(Tenant).where(Tenant.id.in_(tenant_ids)))
        slug_by_id = {t.id: t.slug for t in tenants.scalars().all()}

    order_responses = [_order_to_response(order, tenant_slug=slug_by_id.get(order.tenant_id)) for order in orders]

    total_pages = math.ceil(total / page_size) if total > 0 else 1
    return PaginatedOrderResponse(
        meta={"page": page, "page_size": page_size, "total": total, "total_pages": total_pages},
        data=order_responses
    )

async def _resolve_optional_tenant_id(tenant_slug: str | None, db: AsyncSession) -> int | None:
    if not tenant_slug:
        return None
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant_id

@platform_plane
async def get_customer_order_service(
    user_id: int, order_id: int, db: AsyncSession, tenant_slug: str | None = None
) -> OrderResponse:
    # tenant_slug is optional: the global "my orders across every store"
    # account view has no store context to scope by. When a caller *does*
    # supply one (e.g. a future in-store account page), an order belonging
    # to the user at a different store must 404, not leak across the
    # boundary -- ownership by user_id alone isn't a store isolation
    # guarantee once a customer's identity spans stores.
    tenant_id = await _resolve_optional_tenant_id(tenant_slug, db)

    query = select(Order).where(Order.id == order_id, Order.user_id == user_id)
    if tenant_id is not None:
        query = query.where(Order.tenant_id == tenant_id)

    result = await db.execute(query.options(selectinload(Order.items)))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return _order_to_response(order)

@platform_plane
async def cancel_customer_order_service(
    user_id: int, order_id: int, db: AsyncSession, tenant_slug: str | None = None
):
    tenant_id = await _resolve_optional_tenant_id(tenant_slug, db)

    query = select(Order).options(selectinload(Order.items)).where(Order.id == order_id, Order.user_id == user_id)
    if tenant_id is not None:
        query = query.where(Order.tenant_id == tenant_id)

    result = await db.execute(query)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status not in ('pending', 'pending_payment'):
        raise HTTPException(status_code=400, detail="Only orders awaiting payment can be cancelled")

    order.status = 'cancelled'
    await restore_stock_for_order(order, db)

    await db.commit()
    return {"status": "ok"}

@platform_plane
async def pay_order_service(
    user_id: int, order_id: int, db: AsyncSession, tenant_slug: str | None = None
) -> OrderResponse:
    tenant_id = await _resolve_optional_tenant_id(tenant_slug, db)

    query = select(Order).options(selectinload(Order.items)).where(Order.id == order_id, Order.user_id == user_id)
    if tenant_id is not None:
        query = query.where(Order.tenant_id == tenant_id)

    result = await db.execute(query)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != 'pending_payment':
        raise HTTPException(status_code=400, detail="Order is not awaiting payment")

    if settings.PAYMENT_PROVIDER == "mock":
        # Dev-only mock gateway: "paying" always succeeds immediately, no
        # external call and no webhook involved.
        order.status = 'processing'
        await db.commit()
        await db.refresh(order)
        return _order_to_response(order)

    # Real gateway: start (or, on a retried call, reuse) a payment and hand
    # the frontend what it needs to complete it (e.g. Stripe Elements +
    # confirmPayment). The order stays 'pending_payment' -- only a verified
    # webhook (see payments_router.py) is allowed to move it to 'processing'.
    provider = get_payment_provider()
    intent = await get_or_create_payment_intent(
        provider,
        existing_provider_ref=order.payment_intent_id,
        amount=order.total_amount,
        currency=settings.STRIPE_CURRENCY,
        reference=order.order_number,
        metadata={"order_id": str(order.id), "tenant_id": str(order.tenant_id)},
        idempotency_key=f"order:{order.id}",
    )
    if order.payment_intent_id != intent.provider_ref:
        order.payment_intent_id = intent.provider_ref
        await db.commit()
        await db.refresh(order)

    response = _order_to_response(order)
    response.payment = PaymentIntentInfo(
        provider=settings.PAYMENT_PROVIDER,
        client_secret=intent.client_secret,
        publishable_key=intent.publishable_key,
    )
    return response


@platform_plane
async def mark_order_paid_by_payment_intent(
    provider_ref: str, amount: int, currency: str, db: AsyncSession
) -> bool:
    """
    Called only from the payments webhook (payments_router.py) after its
    signature has verified -- this is the one place a real gateway payment
    actually turns into 'processing'. `amount`/`currency` are what the
    *provider* reports the payment as (from the verified event, not
    anything client-supplied); they're cross-checked against the order's own
    total before anything is marked paid, so a webhook can never move an
    order to 'processing' for less than it's actually owed. Returns False
    for a provider_ref that matches no order/master_order (an unrelated
    event, or a stale retry), which the webhook treats as a no-op rather
    than an error.
    """
    result = await db.execute(select(Order).where(Order.payment_intent_id == provider_ref))
    order = result.scalar_one_or_none()
    if order:
        if not amount_matches(order.total_amount, amount, currency, settings.STRIPE_CURRENCY):
            logger.error(
                "payment_intent %s amount/currency mismatch for order %s: "
                "event reported %s %s, order total is %s %s -- not marking paid",
                provider_ref, order.id, amount, currency, order.total_amount, settings.STRIPE_CURRENCY,
            )
            return False
        if order.status == 'pending_payment':
            order.status = 'processing'
            await db.commit()
        elif order.status == 'expired':
            # cleanup_abandoned_checkouts already canceled this order's
            # PaymentIntent before expiring it and releasing its stock -- a
            # succeeded event landing anyway (the cancel raced a
            # near-simultaneous confirmation) must NOT silently flip it to
            # 'processing': that stock may already be sold to someone else.
            # Surfaced as an error log for manual reconciliation/refund
            # rather than auto-refunding, which needs its own review.
            logger.error(
                "payment_intent %s succeeded for already-expired order %s -- "
                "stock was released, needs manual reconciliation/refund",
                provider_ref, order.id,
            )
        return True

    result = await db.execute(select(MasterOrder).where(MasterOrder.payment_intent_id == provider_ref))
    master_order = result.scalar_one_or_none()
    if not master_order:
        return False

    if not amount_matches(master_order.total_amount, amount, currency, settings.STRIPE_CURRENCY):
        logger.error(
            "payment_intent %s amount/currency mismatch for master_order %s: "
            "event reported %s %s, master total is %s %s -- not marking paid",
            provider_ref, master_order.id, amount, currency, master_order.total_amount, settings.STRIPE_CURRENCY,
        )
        return False

    sub_orders_result = await db.execute(select(Order).where(Order.master_order_id == master_order.id))
    any_updated = False
    for sub_order in sub_orders_result.scalars().all():
        if sub_order.status == 'pending_payment':
            sub_order.status = 'processing'
            any_updated = True
        elif sub_order.status == 'expired':
            logger.error(
                "payment_intent %s succeeded for master_order %s but sub-order %s is already "
                "expired -- stock was released, needs manual reconciliation/refund",
                provider_ref, master_order.id, sub_order.id,
            )
    if any_updated:
        await db.commit()
    return True

async def get_customer_insights_service(tenant_slug: str, db: AsyncSession, top_n: int = 5) -> dict:
    """
    Built directly on list_tenant_customers_service's existing per-customer
    aggregates (orders_count/total_spent/last_order_at) — no new query shape,
    just summarizing data that's already fetched tenant-scoped.
    """
    customers = await list_tenant_customers_service(tenant_slug, db)

    total_customers = len(customers)
    customers_with_orders = [c for c in customers if c.orders_count > 0]
    repeat_customers = [c for c in customers_with_orders if c.orders_count > 1]
    repeat_rate = (len(repeat_customers) / len(customers_with_orders)) if customers_with_orders else 0.0

    top_spenders = sorted(customers_with_orders, key=lambda c: c.total_spent, reverse=True)[:top_n]
    recent_signups = sorted(customers, key=lambda c: c.created_at, reverse=True)[:top_n]

    return {
        "total_customers": total_customers,
        "customers_with_orders": len(customers_with_orders),
        "repeat_customer_rate": round(repeat_rate, 3),
        "top_spenders": [
            {"email": c.email, "full_name": c.full_name, "orders_count": c.orders_count, "total_spent": c.total_spent}
            for c in top_spenders
        ],
        "recent_signups": [
            {"email": c.email, "full_name": c.full_name, "created_at": c.created_at.isoformat()}
            for c in recent_signups
        ],
    }
