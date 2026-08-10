import math
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
from app.models.tenant import Tenant
from app.models.order import Order, OrderItem
from app.models.user import User
from app.models.catalog import ProductVariant, Product, ProductBundleItem
from app.schemas.order_schemas import PaginatedOrderResponse, OrderResponse, OrderItemResponse
from app.schemas.auth_schemas import CustomerSummaryResponse

PAID_ORDER_STATUSES = ('processing', 'completed')

def _order_to_response(order: Order, customer: User | None = None) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        tenant_id=order.tenant_id,
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

async def list_tenant_orders_service(tenant_slug: str, db: AsyncSession) -> list[OrderResponse]:
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")

    result = await db.execute(
        select(Order, User)
        .join(User, User.id == Order.user_id)
        .where(Order.tenant_id == tenant_id)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
    )
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
        .outerjoin(Order, (Order.user_id == User.id) & (Order.tenant_id == tenant_id))
        .where(User.tenant_id == tenant_id, User.role == 'customer')
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

    valid_statuses = ['pending', 'processing', 'completed', 'cancelled']
    if status not in valid_statuses:
        raise HTTPException(status_code=422, detail="Invalid status transition")

    # If transitioning to cancelled, restore stock
    if status == 'cancelled' and order.status != 'cancelled':
        await restore_stock_for_order(order, db)

    order.status = status
    await db.commit()
    return {"status": "ok", "order_status": order.status}

async def list_customer_orders_service(user_id: int, page: int, page_size: int, db: AsyncSession) -> PaginatedOrderResponse:
    query = select(Order).where(Order.user_id == user_id)
    
    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar_one()
    
    query = query.options(selectinload(Order.items))
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    orders = result.scalars().all()

    order_responses = [_order_to_response(order) for order in orders]

    total_pages = math.ceil(total / page_size) if total > 0 else 1
    return PaginatedOrderResponse(
        meta={"page": page, "page_size": page_size, "total": total, "total_pages": total_pages},
        data=order_responses
    )

async def get_customer_order_service(user_id: int, order_id: int, db: AsyncSession) -> OrderResponse:
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.user_id == user_id)
        .options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return _order_to_response(order)

async def cancel_customer_order_service(user_id: int, order_id: int, db: AsyncSession):
    result = await db.execute(select(Order).options(selectinload(Order.items)).where(Order.id == order_id, Order.user_id == user_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status not in ('pending', 'pending_payment'):
        raise HTTPException(status_code=400, detail="Only orders awaiting payment can be cancelled")

    order.status = 'cancelled'
    await restore_stock_for_order(order, db)

    await db.commit()
    return {"status": "ok"}

async def pay_order_service(user_id: int, order_id: int, db: AsyncSession) -> OrderResponse:
    result = await db.execute(select(Order).options(selectinload(Order.items)).where(Order.id == order_id, Order.user_id == user_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != 'pending_payment':
        raise HTTPException(status_code=400, detail="Order is not awaiting payment")

    # Mock payment gateway: for local/dev use, "paying" always succeeds immediately.
    order.status = 'processing'
    await db.commit()
    await db.refresh(order)

    return _order_to_response(order)
