from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import get_current_user
from app.db.session import get_db
from app.schemas.auth_schemas import UserResponse
from app.schemas.order_schemas import PaginatedOrderResponse, OrderResponse
from app.models.user import User
from app.services.order_service import (
    list_customer_orders_service, get_customer_order_service, cancel_customer_order_service,
    pay_order_service
)

customer_router = APIRouter(prefix="/api/v1/customer", tags=["Customer Portal"])

@customer_router.get(
    "/me", 
    response_model=UserResponse,
    summary="Get Customer Profile",
    description="Returns the currently authenticated customer's profile details. Requires a valid JWT bearer token.",
    responses={
        200: {"description": "Customer profile retrieved."},
        401: {"description": "Unauthorized. Missing or invalid token."}
    }
)
async def get_customer_profile(current_user: User = Depends(get_current_user)):
    return current_user

@customer_router.get(
    "/orders", 
    response_model=PaginatedOrderResponse,
    summary="List Customer Orders",
    description="Lists all past and present orders for the authenticated customer. Includes pagination.",
    responses={
        200: {"description": "List of orders successfully retrieved."}
    }
)
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    tenant_slug: str | None = Query(None, description="When set, only return orders for this store."),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await list_customer_orders_service(current_user.id, page, page_size, db, tenant_slug=tenant_slug)

@customer_router.get(
    "/orders/{order_id}", 
    response_model=OrderResponse,
    summary="Get Order Details",
    description="Retrieves full details of a specific order belonging to the authenticated customer. Access is restricted to the order owner.",
    responses={
        200: {"description": "Order details successfully retrieved."},
        404: {"description": "Order not found or does not belong to the user."}
    }
)
async def get_order(
    order_id: int = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await get_customer_order_service(current_user.id, order_id, db)

@customer_router.delete(
    "/orders/{order_id}",
    summary="Cancel Pending Order",
    description="Cancels an order if it is still awaiting payment ('pending' or 'pending_payment'). Orders in 'processing' or 'completed' states cannot be cancelled by the customer.",
    responses={
        200: {"description": "Order successfully cancelled."},
        400: {"description": "Order is no longer awaiting payment and cannot be cancelled."},
        404: {"description": "Order not found."}
    }
)
async def cancel_order(
    order_id: int = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await cancel_customer_order_service(current_user.id, order_id, db)

@customer_router.post(
    "/orders/{order_id}/pay",
    response_model=OrderResponse,
    summary="Pay for an Order (Mock)",
    description="Development-only mock payment gateway: immediately marks an order awaiting payment as paid ('processing'). Real payment processing is not implemented.",
    responses={
        200: {"description": "Payment successful, order is now processing."},
        400: {"description": "Order is not awaiting payment."},
        404: {"description": "Order not found."}
    }
)
async def pay_order(
    order_id: int = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await pay_order_service(current_user.id, order_id, db)
