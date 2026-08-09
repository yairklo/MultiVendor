from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import get_current_user, get_current_customer
from app.db.session import get_db
from app.schemas.auth_schemas import UserResponse
from app.schemas.order_schemas import PaginatedOrderResponse, OrderResponse
from app.models.user import User
from app.services.order_service import (
    list_customer_orders_service, get_customer_order_service, cancel_customer_order_service
)

customer_router = APIRouter(prefix="/api/v1/customer", tags=["Customer Portal"])

@customer_router.get("/me", response_model=UserResponse)
async def get_customer_profile(current_user: User = Depends(get_current_user)):
    """Returns currently authenticated customer details."""
    return current_user

@customer_router.get("/orders", response_model=PaginatedOrderResponse)
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db)
):
    return await list_customer_orders_service(current_user.id, page, page_size, db)

@customer_router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int = Path(...),
    current_user: User = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db)
):
    return await get_customer_order_service(current_user.id, order_id, db)

@customer_router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: int = Path(...),
    current_user: User = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db)
):
    return await cancel_customer_order_service(current_user.id, order_id, db)
