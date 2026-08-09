from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.models.tenant import Tenant
from app.models.order import Order

async def update_order_status_service(tenant_slug: str, order_id: int, status: str, db: AsyncSession):
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Tenant not found")

    order_result = await db.execute(select(Order).where(Order.id == order_id, Order.tenant_id == tenant_id))
    order = order_result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    valid_statuses = ['pending', 'processing', 'completed', 'cancelled']
    if status not in valid_statuses:
        raise HTTPException(status_code=422, detail="Invalid status transition")

    order.status = status
    await db.commit()
    return {"status": "ok", "order_status": order.status}

import math
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from app.schemas.order_schemas import PaginatedOrderResponse, OrderResponse, OrderItemResponse

async def list_customer_orders_service(user_id: int, page: int, page_size: int, db: AsyncSession) -> PaginatedOrderResponse:
    query = select(Order).where(Order.user_id == user_id)
    
    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar_one()
    
    query = query.options(selectinload(Order.items))
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    orders = result.scalars().all()
    
    order_responses = []
    for order in orders:
        order_responses.append(OrderResponse(
            id=order.id,
            tenant_id=order.tenant_id,
            customer_id=order.user_id,
            order_number=order.order_number,
            subtotal=order.subtotal,
            discount_amt=order.discount_amt,
            total_amount=order.total_amount,
            status=order.status,
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
        ))
        
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
        
    return OrderResponse(
        id=order.id,
        tenant_id=order.tenant_id,
        customer_id=order.user_id,
        order_number=order.order_number,
        subtotal=order.subtotal,
        discount_amt=order.discount_amt,
        total_amount=order.total_amount,
        status=order.status,
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

async def cancel_customer_order_service(user_id: int, order_id: int, db: AsyncSession):
    result = await db.execute(select(Order).where(Order.id == order_id, Order.user_id == user_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    if order.status != 'pending':
        raise HTTPException(status_code=400, detail="Only pending orders can be cancelled")
        
    order.status = 'cancelled'
    await db.commit()
    return {"status": "ok"}

