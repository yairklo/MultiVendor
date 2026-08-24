from fastapi import APIRouter, Depends, status, Path, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from app.core.config import settings
from app.core.cart_token import GUEST_CART_TTL_SECONDS
from app.db.session import get_db
from app.deps import get_current_tenant, get_optional_user, get_tenant_customer
from app.models.user import User
from app.schemas.order_schemas import (
    AddToCartRequest, CartResponse, CheckoutRequest, OrderResponse, CartItemResponse, UpdateCartItemRequest,
    StatusResponse, CouponResponse
)
from app.services.checkout_service import (
    add_to_cart_service, get_cart_service, remove_from_cart_service,
    update_cart_item_service, checkout_service, validate_coupon_service, CartCookieAction
)
from app.core.limiter import limiter

cart_router = APIRouter(
    prefix="/api/v1/store/{tenant_slug}",
    tags=["Cart & Checkout"],
    dependencies=[Depends(get_current_tenant)],
)

# A guest cart's capability token lives in an HttpOnly cookie -- never in a
# response body or a header the frontend has to read and store itself,
# which is exactly what would let a stray XSS payload exfiltrate it (see
# app/services/checkout_service.CartCookieAction). Secure is gated on
# APP_ENV rather than always-on because this is also what local dev over
# plain http runs on; browsers silently refuse to set a Secure cookie over
# http, which would break the guest cart flow entirely in dev.
CART_TOKEN_COOKIE = "cart_token"


def _apply_cart_cookie(response: Response, action: CartCookieAction) -> None:
    if action.mint_token:
        response.set_cookie(
            key=CART_TOKEN_COOKIE,
            value=action.mint_token,
            max_age=GUEST_CART_TTL_SECONDS,
            httponly=True,
            secure=settings.APP_ENV == "production",
            samesite="lax",
            path="/",
        )
    elif action.clear:
        response.delete_cookie(key=CART_TOKEN_COOKIE, path="/")


@cart_router.post(
    "/cart/{cart_id}/items",
    response_model=StatusResponse,
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
    request: Request,
    response: Response,
    tenant_slug: str = Path(...),
    cart_id: UUID = Path(...),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = user.id if user else None
    cookie_action = CartCookieAction()
    result = await add_to_cart_service(
        tenant_slug, cart_id, req, user_id, db,
        cart_token=request.cookies.get(CART_TOKEN_COOKIE), cookie_action=cookie_action,
    )
    _apply_cart_cookie(response, cookie_action)
    return result

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
    request: Request,
    response: Response,
    tenant_slug: str = Path(...),
    cart_id: UUID = Path(...),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    cookie_action = CartCookieAction()
    result = await get_cart_service(
        tenant_slug, cart_id, user.id if user else None, db,
        cart_token=request.cookies.get(CART_TOKEN_COOKIE), cookie_action=cookie_action,
    )
    _apply_cart_cookie(response, cookie_action)
    return result

@cart_router.delete(
    "/cart/{cart_id}/items/{item_id}",
    response_model=StatusResponse,
    summary="Remove Item from Cart",
    description="Removes a specific line item from the shopping cart.",
    responses={
        200: {"description": "Item successfully removed."},
        404: {"description": "Item not found in cart."}
    }
)
async def remove_from_cart(
    request: Request,
    response: Response,
    tenant_slug: str = Path(...),
    cart_id: UUID = Path(...),
    item_id: int = Path(...),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    cookie_action = CartCookieAction()
    result = await remove_from_cart_service(
        tenant_slug, cart_id, item_id, user.id if user else None, db,
        cart_token=request.cookies.get(CART_TOKEN_COOKIE), cookie_action=cookie_action,
    )
    _apply_cart_cookie(response, cookie_action)
    return result

@cart_router.patch(
    "/cart/{cart_id}/items/{item_id}",
    response_model=StatusResponse,
    summary="Update Cart Item Quantity",
    description="Sets the exact quantity for a cart line item. Validates the new quantity against available stock.",
    responses={
        200: {"description": "Quantity updated."},
        400: {"description": "Not enough stock for the requested quantity."},
        404: {"description": "Item not found in cart."}
    }
)
async def update_cart_item(
    req: UpdateCartItemRequest,
    request: Request,
    response: Response,
    tenant_slug: str = Path(...),
    cart_id: UUID = Path(...),
    item_id: int = Path(...),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    cookie_action = CartCookieAction()
    result = await update_cart_item_service(
        tenant_slug, cart_id, item_id, req.quantity, user.id if user else None, db,
        cart_token=request.cookies.get(CART_TOKEN_COOKIE), cookie_action=cookie_action,
    )
    _apply_cart_cookie(response, cookie_action)
    return result

@cart_router.post(
    "/coupons/validate",
    response_model=CouponResponse,
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
@limiter.limit("20/minute")
async def checkout(
    request: Request,
    response: Response,
    req: CheckoutRequest,
    tenant_slug: str = Path(...),
    user: User = Depends(get_tenant_customer),
    db: AsyncSession = Depends(get_db),
):
    cookie_action = CartCookieAction()
    result = await checkout_service(
        tenant_slug, req, user.id, db,
        cart_token=request.cookies.get(CART_TOKEN_COOKIE), cookie_action=cookie_action,
    )
    _apply_cart_cookie(response, cookie_action)
    return result
