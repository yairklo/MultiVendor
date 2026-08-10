from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from app.schemas.common_schemas import PaginatedResponse, OrderStatus, DiscountType

class AddToCartRequest(BaseModel):
    variant_id: int
    quantity: int = Field(1, ge=1)
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "variant_id": 50,
            "quantity": 2
        }
    })

class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(..., ge=1)
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "quantity": 3
        }
    })

class CartItemResponse(BaseModel):
    id: int
    variant_id: int
    product_name: str
    product_type: str
    sku: str
    attributes: Dict[str, Any]
    unit_price: Decimal
    quantity: int
    total_price: Decimal
    image_url: Optional[str] = None

class CartResponse(BaseModel):
    cart_id: UUID
    tenant_id: int
    items: List[CartItemResponse]
    subtotal: Decimal

class CheckoutRequest(BaseModel):
    cart_id: UUID
    coupon_code: Optional[str] = None
    shipping_address: Optional[Dict[str, Any]] = None
    shipping_method_id: Optional[int] = None
    payment_token: UUID
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "cart_id": "123e4567-e89b-12d3-a456-426614174000",
            "coupon_code": "SUMMER10",
            "shipping_address": {
                "address_line_1": "123 Main St",
                "city": "Tel Aviv",
                "zip": "6100000"
            },
            "shipping_method_id": 1,
            "payment_token": "987e6543-e21b-34d3-b456-426614174999"
        }
    })

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
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    order_number: str
    subtotal: Decimal
    discount_amt: Decimal
    shipping_method_id: Optional[int] = None
    shipping_fee: Decimal = Decimal('0.00')
    total_amount: Decimal
    status: OrderStatus
    order_type: str = 'physical'
    shipping_info: Optional[Dict[str, Any]] = None
    created_at: datetime
    items: List[OrderItemResponse]
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": 999,
            "tenant_id": 1,
            "customer_id": 12,
            "order_number": "ORD-1A2B3C4D",
            "subtotal": 50.00,
            "discount_amt": 5.00,
            "shipping_method_id": 1,
            "shipping_fee": 10.00,
            "total_amount": 55.00,
            "status": "pending",
            "order_type": "physical",
            "shipping_info": {"city": "Tel Aviv"},
            "created_at": "2026-08-09T10:00:00Z",
            "items": []
        }
    })
    model_config = ConfigDict(from_attributes=True)

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
