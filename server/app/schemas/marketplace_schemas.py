from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from app.schemas.common_schemas import PaginatedResponse
from app.schemas.order_schemas import OrderResponse, PaymentIntentInfo
from app.schemas.catalog_schemas import ProductVariantSchema

class MarketplaceProductResponse(BaseModel):
    """A product surfaced on the cross-store marketplace. Carries its origin
    store alongside the usual product fields so the frontend can link back to
    /store/{tenant_slug}/products/{slug} -- browsing is cross-store, but a
    purchase is still fulfilled by one specific vendor."""
    id: int
    tenant_id: int
    tenant_slug: str
    tenant_name: str
    category_id: Optional[int]
    name: Any
    slug: str
    description: Any
    base_price: Decimal
    product_type: str
    primary_image_url: Optional[str]
    images: List[str]
    average_rating: Optional[float] = None
    review_count: int = 0
    # Included so a listing card can add-to-cart directly (same one-click,
    # first-variant convention as storefront/ProductCard) without a second
    # round trip to the product detail endpoint.
    variants: List[ProductVariantSchema] = []
    created_at: datetime

class PaginatedMarketplaceProductResponse(PaginatedResponse):
    data: List[MarketplaceProductResponse]

class MarketplaceAddToCartRequest(BaseModel):
    variant_id: int
    quantity: int = Field(1, ge=1)

class MarketplaceCartItemResponse(BaseModel):
    id: int
    tenant_id: int
    tenant_slug: str
    tenant_name: str
    variant_id: int
    product_name: str
    sku: str
    unit_price: Decimal
    quantity: int
    total_price: Decimal
    image_url: Optional[str] = None
    # Lets the checkout page decide whether to show the shipping-address
    # form at all -- mirrors the single-store checkout's use of this same
    # field (see checkout/page.tsx's isDigitalOnly).
    product_type: str

class MarketplaceCartResponse(BaseModel):
    cart_id: UUID
    items: List[MarketplaceCartItemResponse]
    subtotal: Decimal
    vendor_count: int

class MarketplaceCheckoutRequest(BaseModel):
    cart_id: UUID
    shipping_address: Optional[Dict[str, Any]] = None
    payment_token: UUID
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "cart_id": "123e4567-e89b-12d3-a456-426614174000",
            "shipping_address": {
                "address_line_1": "123 Main St",
                "city": "Tel Aviv",
                "zip": "6100000"
            },
            "payment_token": "987e6543-e21b-34d3-b456-426614174999"
        }
    })

class MasterOrderResponse(BaseModel):
    id: int
    master_order_number: str
    total_amount: Decimal
    created_at: datetime
    sub_orders: List[OrderResponse]
    payment: Optional[PaymentIntentInfo] = None
