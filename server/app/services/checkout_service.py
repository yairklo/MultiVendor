import asyncio
import uuid
import json
from decimal import Decimal
from typing import Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.session import redis_client
from app.db.tenant_context import unscoped
from app.core.cart_token import issue_guest_cart_token, verify_guest_cart_token
from app.models.tenant import Tenant
from app.models.catalog import ProductVariant, Product, ProductBundleItem
from app.models.order import Cart, CartItem, Order, OrderItem, ShippingMethod
from app.models.coupon import Coupon
from app.schemas.order_schemas import (
    AddToCartRequest, CartResponse, CartItemResponse,
    CheckoutRequest, OrderResponse, OrderItemResponse
)
from datetime import datetime, timezone

def _resolve_product_name(name) -> str:
    if isinstance(name, dict):
        return name.get('en') or next(iter(name.values()), '')
    return str(name)

async def _resolve_tenant_id(tenant_slug: str, db: AsyncSession) -> int:
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Store not found")
    return tenant_id

def _assert_cart_ownership(
    cart: Cart, user_id: Optional[int], cart_token: Optional[str], *, claim: bool = False
) -> None:
    if cart.user_id is not None:
        # Claimed cart: ownership is the authenticated user, full stop. The
        # capability token was only ever needed while the cart was unclaimed.
        if user_id is None or cart.user_id != user_id:
            raise HTTPException(status_code=404, detail="Cart not found")
        return

    # Still a guest cart: Cart.id is a client-generated UUID with no secrecy
    # of its own, so the bare id must never be sufficient to read/mutate it.
    # Only the capability token minted when the cart was created proves the
    # caller is the party it was created for.
    if not cart_token or not verify_guest_cart_token(cart_token, cart.id):
        raise HTTPException(status_code=404, detail="Cart not found")

    if claim and user_id is not None:
        cart.user_id = user_id

async def add_to_cart_service(
    tenant_slug: str, cart_id: UUID, req: AddToCartRequest, user_id: Optional[int], db: AsyncSession,
    cart_token: Optional[str] = None,
):
    tenant_id = await _resolve_tenant_id(tenant_slug, db)

    cart_result = await db.execute(select(Cart).where(Cart.id == str(cart_id)))
    cart = cart_result.scalar_one_or_none()

    if not cart:
        with unscoped():
            foreign = await db.execute(select(Cart.id).where(Cart.id == str(cart_id)))
        if foreign.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Cart not found")

    minted_token = None
    if not cart:
        cart = Cart(id=str(cart_id), tenant_id=tenant_id, user_id=user_id)
        db.add(cart)
        await db.flush()
        if user_id is None:
            minted_token = issue_guest_cart_token(str(cart_id))
    else:
        _assert_cart_ownership(cart, user_id, cart_token, claim=True)

    variant_result = await db.execute(
        select(ProductVariant)
        .join(Product)
        .where(
            ProductVariant.id == req.variant_id, 
            ProductVariant.tenant_id == tenant_id,
            Product.is_active == True
        )
    )
    variant = variant_result.scalar_one_or_none()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found or product inactive")

    if variant.stock_quantity < req.quantity:
        raise HTTPException(status_code=400, detail="Not enough stock")

    item_result = await db.execute(select(CartItem).where(CartItem.cart_id == str(cart_id), CartItem.variant_id == req.variant_id))
    item = item_result.scalar_one_or_none()
    
    if item:
        item.quantity += req.quantity
    else:
        item = CartItem(
            tenant_id=tenant_id,
            cart_id=str(cart_id),
            variant_id=req.variant_id,
            quantity=req.quantity
        )
        db.add(item)

    await db.commit()
    return {"status": "ok", "cart_token": minted_token}

async def get_cart_service(
    tenant_slug: str, cart_id: UUID, user_id: Optional[int], db: AsyncSession,
    cart_token: Optional[str] = None,
) -> CartResponse:
    tenant_id = await _resolve_tenant_id(tenant_slug, db)

    cart_result = await db.execute(
        select(Cart)
        .where(Cart.id == str(cart_id), Cart.tenant_id == tenant_id)
        .options(
            selectinload(Cart.items)
            .selectinload(CartItem.variant)
            .selectinload(ProductVariant.product)
            .selectinload(Product.images)
        )
    )
    cart = cart_result.scalar_one_or_none()
    if not cart:
        with unscoped():
            foreign = await db.execute(select(Cart.id).where(Cart.id == str(cart_id)))
        if foreign.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Cart not found")
        return CartResponse(cart_id=cart_id, tenant_id=tenant_id, items=[], subtotal=Decimal("0.00"))

    _assert_cart_ownership(cart, user_id, cart_token, claim=True)
    if user_id is not None:
        # A viewed guest cart claimed above needs the ownership change persisted --
        # this is the "touch the cart after login and it's now yours" path.
        await db.commit()

    items = []
    subtotal = Decimal("0.00")
    for item in cart.items:
        variant = item.variant
        product = variant.product
        unit_price = variant.price_override if variant.price_override is not None else product.base_price
        total_price = unit_price * item.quantity
        subtotal += total_price
        
        product_name = _resolve_product_name(product.name)

        image_url = next((img.image_url for img in product.images if img.is_primary), None)
        if not image_url and product.images:
            image_url = product.images[0].image_url

        items.append(CartItemResponse(
            id=item.id,
            variant_id=variant.id,
            product_name=product_name,
            product_type=product.product_type,
            sku=variant.sku,
            attributes=variant.attributes_json or {},
            unit_price=unit_price,
            quantity=item.quantity,
            total_price=total_price,
            image_url=image_url
        ))

    return CartResponse(
        cart_id=cart_id,
        tenant_id=cart.tenant_id,
        items=items,
        subtotal=subtotal
    )

async def remove_from_cart_service(
    tenant_slug: str, cart_id: UUID, item_id: int, user_id: Optional[int], db: AsyncSession,
    cart_token: Optional[str] = None,
):
    tenant_id = await _resolve_tenant_id(tenant_slug, db)
    cart_result = await db.execute(select(Cart).where(Cart.id == str(cart_id), Cart.tenant_id == tenant_id))
    cart = cart_result.scalar_one_or_none()
    if not cart:
        raise HTTPException(status_code=404, detail="Item not found")
    _assert_cart_ownership(cart, user_id, cart_token, claim=True)

    item_result = await db.execute(
        select(CartItem).join(Cart).where(Cart.id == str(cart_id), Cart.tenant_id == tenant_id, CartItem.id == item_id)
    )
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    await db.delete(item)
    await db.commit()
    return {"status": "ok"}

async def update_cart_item_service(
    tenant_slug: str, cart_id: UUID, item_id: int, quantity: int, user_id: Optional[int], db: AsyncSession,
    cart_token: Optional[str] = None,
):
    tenant_id = await _resolve_tenant_id(tenant_slug, db)
    cart_result = await db.execute(select(Cart).where(Cart.id == str(cart_id), Cart.tenant_id == tenant_id))
    cart = cart_result.scalar_one_or_none()
    if not cart:
        raise HTTPException(status_code=404, detail="Item not found")
    _assert_cart_ownership(cart, user_id, cart_token, claim=True)

    item_result = await db.execute(
        select(CartItem).join(Cart).where(Cart.id == str(cart_id), Cart.tenant_id == tenant_id, CartItem.id == item_id)
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

async def validate_coupon_service(tenant_slug: str, coupon_code: str, db: AsyncSession):
    tenant_result = await db.execute(select(Tenant.id).where(Tenant.slug == tenant_slug))
    tenant_id = tenant_result.scalar_one_or_none()
    if not tenant_id:
        raise HTTPException(status_code=404, detail="Store not found")

    coupon_result = await db.execute(
        select(Coupon).where(Coupon.tenant_id == tenant_id, Coupon.code == coupon_code)
    )
    coupon = coupon_result.scalar_one_or_none()
    
    if not coupon:
        raise HTTPException(status_code=400, detail="Invalid coupon")

    if not coupon.is_active:
        raise HTTPException(status_code=400, detail="Coupon is disabled")

    if coupon.valid_until and coupon.valid_until.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Coupon expired")
        
    if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
        raise HTTPException(status_code=400, detail="Coupon usage limit reached")

    return coupon

async def checkout_service(
    tenant_slug: str, req: CheckoutRequest, user_id: int, db: AsyncSession,
    cart_token: Optional[str] = None,
) -> OrderResponse:
    tenant_id = await _resolve_tenant_id(tenant_slug, db)

    cart_result = await db.execute(
        select(Cart)
        .where(Cart.id == str(req.cart_id), Cart.tenant_id == tenant_id)
        .options(selectinload(Cart.items).selectinload(CartItem.variant).selectinload(ProductVariant.product))
    )
    cart = cart_result.scalar_one_or_none()

    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty or not found")

    _assert_cart_ownership(cart, user_id, cart_token, claim=True)

    # Analyze order type and gather variants to lock
    is_entirely_digital = True
    variants_to_lock = [] # List of tuples (variant_id, qty_needed)
    
    for item in cart.items:
        product = item.variant.product
        if product.product_type != 'digital':
            is_entirely_digital = False
            
        if product.is_bundle:
            # Fetch bundle components
            bundle_res = await db.execute(select(ProductBundleItem).where(ProductBundleItem.bundle_product_id == product.id))
            components = bundle_res.scalars().all()
            for comp in components:
                variants_to_lock.append((comp.component_variant_id, item.quantity * comp.quantity))
        else:
            variants_to_lock.append((item.variant.id, item.quantity))
            
    if not is_entirely_digital and not req.shipping_address:
        raise HTTPException(status_code=400, detail="Shipping address is required for physical goods")

    shipping_fee = Decimal("0.00")
    if req.shipping_method_id and not is_entirely_digital:
        sm_res = await db.execute(select(ShippingMethod).where(ShippingMethod.id == req.shipping_method_id, ShippingMethod.tenant_id == tenant_id))
        sm = sm_res.scalar_one_or_none()
        if sm:
            shipping_fee = sm.price # basic logic
        else:
            req.shipping_method_id = None

    # Sort variants to prevent deadlocks
    variants_to_lock.sort(key=lambda x: x[0])
    
    # Consolidate quantities for same variant
    consolidated_locks = {}
    for vid, qty in variants_to_lock:
        consolidated_locks[vid] = consolidated_locks.get(vid, 0) + qty

    locks = []
    try:
        # Acquire locks
        for vid in consolidated_locks.keys():
            lock_key = f"lock:tenant:{tenant_id}:variant:{vid}"
            lock = redis_client.lock(lock_key, timeout=10)
            acquired = await lock.acquire(blocking=False)
            if not acquired:
                raise HTTPException(status_code=409, detail=f"Variant {vid} is currently being checked out by someone else")
            locks.append(lock)

        # Re-fetch stock and calculate subtotal
        subtotal = Decimal("0.00")
        order_items_data = []
        
        # Deduct consolidated stocks
        for vid, qty in consolidated_locks.items():
            variant_result = await db.execute(select(ProductVariant).where(ProductVariant.id == vid))
            variant = variant_result.scalar_one()
            if variant.stock_quantity < qty:
                raise HTTPException(status_code=400, detail=f"Not enough stock for variant {vid}")
            variant.stock_quantity -= qty
            
        # Calculate totals from cart items
        for item in cart.items:
            unit_price = item.variant.price_override if item.variant.price_override is not None else item.variant.product.base_price
            total_price = unit_price * item.quantity
            subtotal += total_price
            
            order_items_data.append({
                "variant_id": item.variant.id,
                "product_name": _resolve_product_name(item.variant.product.name),
                "sku": item.variant.sku,
                "unit_price": unit_price,
                "quantity": item.quantity
            })

        # Process coupon
        discount_amt = Decimal("0.00")
        coupon = None
        if req.coupon_code:
            try:
                coupon = await validate_coupon_service(tenant_slug, req.coupon_code, db)
                if subtotal < coupon.min_order_amt:
                    raise HTTPException(status_code=400, detail=f"Minimum order amount is {coupon.min_order_amt}")
                
                if coupon.discount_type == 'percentage':
                    discount_amt = subtotal * (coupon.discount_val / 100)
                else:
                    discount_amt = coupon.discount_val
                
                coupon.used_count += 1
            except HTTPException as e:
                raise e

        total_amount = subtotal - discount_amt + shipping_fee
        if total_amount < Decimal("0.00"):
            total_amount = Decimal("0.00")

        # Create Order
        order = Order(
            tenant_id=tenant_id,
            user_id=user_id,
            coupon_id=coupon.id if coupon else None,
            order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            subtotal=subtotal,
            discount_amt=discount_amt,
            shipping_method_id=req.shipping_method_id if not is_entirely_digital else None,
            shipping_fee=shipping_fee,
            total_amount=total_amount,
            status='pending_payment',
            order_type='digital' if is_entirely_digital else 'physical',
            shipping_json=req.shipping_address if not is_entirely_digital else None
        )
        db.add(order)
        await db.flush()

        for data in order_items_data:
            order_item = OrderItem(
                tenant_id=tenant_id,
                order_id=order.id,
                variant_id=data["variant_id"],
                product_name=data["product_name"],
                sku=data["sku"],
                unit_price=data["unit_price"],
                quantity=data["quantity"]
            )
            db.add(order_item)

        await db.delete(cart)
        await db.commit()
        await db.refresh(order)
        
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
                id=i.id,
                variant_id=i.variant_id,
                product_name=i.product_name,
                sku=i.sku,
                unit_price=i.unit_price,
                quantity=i.quantity
            ) for i in (await db.scalars(select(OrderItem).where(OrderItem.order_id == order.id))).all()]
        )
        
    finally:
        for lock in locks:
            try:
                await lock.release()
            except Exception:
                pass
