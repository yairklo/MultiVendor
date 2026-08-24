from fastapi import APIRouter, Depends, status, Query, Path, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from app.core.config import settings
from app.core.cart_token import GUEST_CART_TTL_SECONDS
from app.db.session import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.marketplace_schemas import (
    PaginatedMarketplaceProductResponse, MarketplaceAddToCartRequest, MarketplaceCartResponse,
    MarketplaceCheckoutRequest, MasterOrderResponse,
)
from app.schemas.order_schemas import StatusResponse, UpdateCartItemRequest
from app.services.catalog_service import list_marketplace_products_service
from app.services.checkout_service import CartCookieAction
from app.services.marketplace_service import (
    add_to_marketplace_cart_service, get_marketplace_cart_service, remove_from_marketplace_cart_service,
    update_marketplace_cart_item_service, marketplace_checkout_service, get_master_order_service,
    pay_master_order_service,
)
from app.core.limiter import limiter

marketplace_router = APIRouter(prefix="/api/v1/marketplace", tags=["Marketplace"])

# Distinct from cart_router.py's CART_TOKEN_COOKIE -- a shopper can hold both
# a single-store guest cart and a marketplace guest cart at once (the
# frontend already keeps them in separate localStorage keys), so they need
# separate cookies too.
MARKETPLACE_CART_TOKEN_COOKIE = "marketplace_cart_token"


def _apply_cart_cookie(response: Response, action: CartCookieAction) -> None:
    if action.mint_token:
        response.set_cookie(
            key=MARKETPLACE_CART_TOKEN_COOKIE,
            value=action.mint_token,
            max_age=GUEST_CART_TTL_SECONDS,
            httponly=True,
            secure=settings.APP_ENV == "production",
            samesite="lax",
            path="/",
        )
    elif action.clear:
        response.delete_cookie(key=MARKETPLACE_CART_TOKEN_COOKIE, path="/")

@marketplace_router.get(
    "/products",
    response_model=PaginatedMarketplaceProductResponse,
    summary="List Marketplace Products",
    description="Lists products opted into the cross-store marketplace, from any active store. Each result carries its origin tenant_slug so the frontend can link back to that store's product page.",
)
async def list_marketplace_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    q: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await list_marketplace_products_service(page, page_size, q, db)

@marketplace_router.post(
    "/cart/{cart_id}/items",
    response_model=StatusResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Item to Marketplace Cart",
    description="Adds a product variant (from any store) to a cross-store marketplace cart, identified purely by its own variant_id -- the owning tenant is resolved from the variant.",
)
async def add_to_marketplace_cart(
    req: MarketplaceAddToCartRequest,
    request: Request,
    response: Response,
    cart_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
):
    cookie_action = CartCookieAction()
    result = await add_to_marketplace_cart_service(
        cart_id, req, db,
        cart_token=request.cookies.get(MARKETPLACE_CART_TOKEN_COOKIE), cookie_action=cookie_action,
    )
    _apply_cart_cookie(response, cookie_action)
    return result

@marketplace_router.get(
    "/cart/{cart_id}",
    response_model=MarketplaceCartResponse,
    summary="View Marketplace Cart",
    description="Retrieves the cross-store cart, grouped implicitly by tenant via each item's tenant_slug/tenant_name.",
)
async def get_marketplace_cart(
    request: Request,
    cart_id: UUID = Path(...),
    db: AsyncSession = Depends(get_db),
):
    return await get_marketplace_cart_service(
        cart_id, db, cart_token=request.cookies.get(MARKETPLACE_CART_TOKEN_COOKIE)
    )

@marketplace_router.delete(
    "/cart/{cart_id}/items/{item_id}",
    response_model=StatusResponse,
    summary="Remove Item from Marketplace Cart",
)
async def remove_from_marketplace_cart(
    request: Request,
    cart_id: UUID = Path(...),
    item_id: int = Path(...),
    db: AsyncSession = Depends(get_db),
):
    return await remove_from_marketplace_cart_service(
        cart_id, item_id, db, cart_token=request.cookies.get(MARKETPLACE_CART_TOKEN_COOKIE)
    )

@marketplace_router.patch(
    "/cart/{cart_id}/items/{item_id}",
    response_model=StatusResponse,
    summary="Update Marketplace Cart Item Quantity",
)
async def update_marketplace_cart_item(
    req: UpdateCartItemRequest,
    request: Request,
    cart_id: UUID = Path(...),
    item_id: int = Path(...),
    db: AsyncSession = Depends(get_db),
):
    return await update_marketplace_cart_item_service(
        cart_id, item_id, req.quantity, db, cart_token=request.cookies.get(MARKETPLACE_CART_TOKEN_COOKIE)
    )

@marketplace_router.post(
    "/checkout",
    response_model=MasterOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Marketplace Checkout (Order Splitting)",
    description=(
        "Checks out a cross-store cart in one call. Cart items are grouped by vendor (tenant_id), stock is "
        "locked and validated per vendor with the same Redis distributed-lock strategy as the single-store "
        "checkout, and one sub-order is created per vendor under a shared master order. Each sub-order carries "
        "its own subtotal, platform_commission, and vendor_net_payout. A global customer's membership at each "
        "vendor is created automatically if this is their first purchase there."
    ),
    responses={
        201: {"description": "Checkout successful. Master order plus one sub-order per vendor generated."},
        400: {"description": "Cart is empty or out of stock."},
        409: {"description": "Concurrency conflict on one of the vendors' stock."},
    },
)
@limiter.limit("20/minute")
async def marketplace_checkout(
    request: Request,
    response: Response,
    req: MarketplaceCheckoutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await marketplace_checkout_service(
        req, user.id, db, cart_token=request.cookies.get(MARKETPLACE_CART_TOKEN_COOKIE)
    )
    # Checkout consumes (deletes) the cart's items -- nothing left for the
    # capability cookie to protect once it succeeds.
    response.delete_cookie(key=MARKETPLACE_CART_TOKEN_COOKIE, path="/")
    return result

@marketplace_router.get(
    "/orders/{master_order_id}",
    response_model=MasterOrderResponse,
    summary="Get Master Order Details",
    description="Retrieves a master order and its per-vendor sub-orders. Access is restricted to the order's owner.",
    responses={404: {"description": "Order not found or does not belong to the user."}},
)
async def get_master_order(
    master_order_id: int = Path(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_master_order_service(master_order_id, user.id, db)

@marketplace_router.post(
    "/orders/{master_order_id}/pay",
    response_model=MasterOrderResponse,
    summary="Pay for a Master Order",
    description="Starts payment for every vendor sub-order awaiting payment under this master order. With PAYMENT_PROVIDER=mock (default), all of them are immediately marked paid ('processing') in one call. With PAYMENT_PROVIDER=stripe, one PaymentIntent is started for the whole multi-vendor total; every sub-order moves to 'processing' together once the Stripe webhook confirms it.",
    responses={
        200: {"description": "Mock: payment successful, all sub-orders now processing. Stripe: PaymentIntent started, response includes `payment.client_secret`."},
        400: {"description": "No sub-order is awaiting payment."},
        404: {"description": "Order not found or does not belong to the user."},
    },
)
async def pay_master_order(
    master_order_id: int = Path(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await pay_master_order_service(master_order_id, user.id, db)
