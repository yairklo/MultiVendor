from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from app.schemas.common_schemas import PaginatedResponse, OrderStatus, DiscountType

class AddToCartRequest(BaseModel):
    variant_id: int
    quantity: int = Field(1, ge=1)

class CartItemResponse(BaseModel):
    id: int
    variant_id: int
    product_name: str
    sku: str
    attributes: Dict[str, Any]
    unit_price: Decimal
    quantity: int
    total_price: Decimal

class CartResponse(BaseModel):
    cart_id: UUID
    tenant_id: int
    items: List[CartItemResponse]
    subtotal: Decimal

class CheckoutRequest(BaseModel):
    cart_id: UUID
    coupon_code: Optional[str] = None
    shipping_address: Dict[str, Any]
    payment_token: UUID

class OrderItemResponse(BaseModel):
    id: int
    variant_id: Optional[int]
    product_name: str
    sku: str
    unit_price: Decimal
    quantity: int

class OrderResponse(BaseModel):
    id: int
    tenant_id: int
    customer_id: int
    order_number: str
    subtotal: Decimal
    discount_amt: Decimal
    total_amount: Decimal
    status: OrderStatus
    shipping_info: Dict[str, Any]
    created_at: datetime
    items: List[OrderItemResponse]

class PaginatedOrderResponse(PaginatedResponse):
    data: List[OrderResponse]

class CouponCreateRequest(BaseModel):
    code: str = Field(..., min_length=3, max_length=20)
    discount_type: DiscountType
    discount_val: Decimal = Field(..., gt=0)
    min_order_amt: Decimal = Decimal("0.00")
    usage_limit: int = Field(100, gt=0)
    valid_until: datetime

class CouponResponse(BaseModel):
    id: int
    code: str
    discount_type: DiscountType
    discount_val: Decimal
    used_count: int
    valid_until: datetime
