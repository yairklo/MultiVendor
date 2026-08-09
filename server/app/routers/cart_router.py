from fastapi import APIRouter, Depends, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from app.db.session import get_db
from app.deps import get_optional_user, get_current_customer
from app.models.user import User
from app.schemas.order_schemas import (
    AddToCartRequest, CartResponse, CheckoutRequest, OrderResponse, CartItemResponse
)
from app.services.checkout_service import (
    add_to_cart_service, get_cart_service, remove_from_cart_service,
    checkout_service, validate_coupon_service
)

cart_router = APIRouter(prefix="/api/v1/store/{tenant_slug}", tags=["Cart & Checkout"])

@cart_router.post(
    "/cart/{cart_id}/items", 
    status_code=status.HTTP_201_CREATED,
    summary="Add Item to Cart",
    description="Adds a product variant to the specified shopping cart. Creates the cart if it doesn't exist. Validates that the variant is active and has sufficient stock available.",
    responses={
        201: {"description": "Item successfully added to cart."},
        400: {"description": "Variant not found, product inactive, or insufficient stock."},
        404: {"description": "Tenant store not found."}
    }
)
async def add_to_cart(
    req: AddToCartRequest,
    tenant_slug: str = Path(...),
    cart_id: UUID = Path(...),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db)
):
    user_id = user.id if user else None
    return await add_to_cart_service(tenant_slug, cart_id, req, user_id, db)

@cart_router.get(
    "/cart/{cart_id}", 
    response_model=CartResponse,
    summary="View Cart Details",
    description="Retrieves the full cart details including subtotal and all item variants populated with their latest snapshot pricing.",
    responses={
        200: {"description": "Cart successfully retrieved."}
    }
)
async def get_cart(
    tenant_slug: str = Path(...),
    cart_id: UUID = Path(...),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db)
):
    return await get_cart_service(tenant_slug, cart_id, db)

@cart_router.delete(
    "/cart/{cart_id}/items/{item_id}",
    summary="Remove Item from Cart",
    description="Removes a specific line item from the shopping cart.",
    responses={
        200: {"description": "Item successfully removed."},
        404: {"description": "Item not found in cart."}
    }
)
async def remove_from_cart(
    tenant_slug: str = Path(...),
    cart_id: UUID = Path(...),
    item_id: int = Path(...),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db)
):
    return await remove_from_cart_service(tenant_slug, cart_id, item_id, db)

@cart_router.post(
    "/coupons/validate",
    summary="Validate a Coupon Code",
    description="Validates a promotional code against the store's settings. Checks expiration dates, usage limits, and minimum order values.",
    responses={
        200: {"description": "Coupon is valid."},
        400: {"description": "Invalid coupon, expired, or usage limit reached."}
    }
)
async def validate_coupon(
    coupon_code: str,
    tenant_slug: str = Path(...),
    db: AsyncSession = Depends(get_db)
):
    return await validate_coupon_service(tenant_slug, coupon_code, db)

@cart_router.post(
    "/cart/checkout", 
    response_model=OrderResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Process Checkout (Concurrency Safe)",
    description="Processes the cart into a finalized Order. Employs **Redis Distributed Locks** (`lock:tenant:variant`) to serialize requests and absolutely prevent overselling of limited inventory. Includes coupon application and stock deduction.",
    responses={
        201: {"description": "Checkout successful. Order generated."},
        400: {"description": "Cart is empty, coupon validation failed, or out of stock."},
        409: {"description": "Concurrency Conflict. Another user is currently purchasing this item."}
    }
)
async def checkout(
    req: CheckoutRequest,
    tenant_slug: str = Path(...),
    user: User = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db)
):
    return await checkout_service(tenant_slug, req, user.id, db)
