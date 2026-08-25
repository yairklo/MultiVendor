from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime
from decimal import Decimal
from app.schemas.common_schemas import PaginatedResponse, ReviewStatus


def normalize_digital_file_url(url: Optional[str]) -> Optional[str]:
    if url is None:
        return None
    stripped = url.strip()
    if not stripped:
        return None
    if len(stripped) > 512:
        raise ValueError("digital_file_url must be at most 512 characters")
    lowered = stripped.lower()
    if lowered.startswith(("javascript:", "data:", "vbscript:")):
        raise ValueError("Invalid digital_file_url")
    if stripped.startswith("/") or lowered.startswith(("http://", "https://")):
        return stripped
    raise ValueError("digital_file_url must be an http(s) URL or a site-relative path")

class ProductVariantSchema(BaseModel):
    id: Optional[int] = None
    sku: str
    attributes_json: Optional[Dict[str, Any]] = Field(default_factory=dict)
    price_override: Optional[Decimal] = None
    stock_quantity: int = Field(..., ge=0)
    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "sku": "TSHIRT-RED-M",
            "attributes_json": {"color": "red", "size": "M"},
            "price_override": 29.99,
            "stock_quantity": 50
        }
    })

class ProductBundleItemSchema(BaseModel):
    component_variant_id: int
    quantity: int = Field(default=1, gt=0)
    model_config = ConfigDict(from_attributes=True)

class ProductCreateRequest(BaseModel):
    category_id: Optional[int] = None
    name: Dict[str, str] = Field(...)
    slug: str = Field(..., pattern="^[a-z0-9-]+$")
    description: Optional[Dict[str, str]] = None
    base_price: Decimal = Field(..., gt=0)
    is_active: bool = True
    show_in_marketplace: bool = False
    product_type: Literal['physical', 'digital', 'service'] = 'physical'
    digital_file_url: Optional[str] = Field(None, max_length=512)
    download_limit: Optional[int] = None
    is_bundle: bool = False
    bundle_items: Optional[List[ProductBundleItemSchema]] = None
    variants: List[ProductVariantSchema]
    images: List[str]
    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "category_id": 1,
            "name": {"he": "חולצה קלאסית", "en": "Classic T-Shirt"},
            "slug": "classic-tshirt",
            "description": {"he": "100% כותנה", "en": "100% Cotton classic fit t-shirt."},
            "base_price": 25.00,
            "is_active": True,
            "variants": [
                {
                    "sku": "TSHIRT-RED-M",
                    "attributes_json": {"color": "red", "size": "M"},
                    "stock_quantity": 50
                }
            ],
            "images": ["https://example.com/images/tshirt1.png"]
        }
    })

    @field_validator("digital_file_url")
    @classmethod
    def _normalize_digital_file_url(cls, v: Optional[str]) -> Optional[str]:
        return normalize_digital_file_url(v)

class ProductUpdateRequest(BaseModel):
    category_id: Optional[int] = None
    name: Optional[Dict[str, str]] = None
    description: Optional[Dict[str, str]] = None
    base_price: Optional[Decimal] = Field(None, gt=0)
    is_active: Optional[bool] = None
    show_in_marketplace: Optional[bool] = None
    product_type: Optional[Literal['physical', 'digital', 'service']] = None
    digital_file_url: Optional[str] = Field(None, max_length=512)
    download_limit: Optional[int] = None
    is_bundle: Optional[bool] = None
    bundle_items: Optional[List[ProductBundleItemSchema]] = None
    images: Optional[List[str]] = None

    @field_validator("digital_file_url")
    @classmethod
    def _normalize_digital_file_url(cls, v: Optional[str]) -> Optional[str]:
        return normalize_digital_file_url(v)

class ProductResponse(BaseModel):
    id: int
    tenant_id: int
    category_id: Optional[int]
    name: Any
    slug: str
    description: Any
    base_price: Decimal
    is_active: bool
    show_in_marketplace: bool = False
    product_type: str
    digital_file_url: Optional[str]
    download_limit: Optional[int]
    is_bundle: bool
    bundle_items: Optional[List[ProductBundleItemSchema]] = None
    variants: List[ProductVariantSchema]
    primary_image_url: Optional[str]
    images: List[str]
    average_rating: Optional[float] = None
    review_count: int = 0
    created_at: datetime
    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": 100,
            "tenant_id": 1,
            "name": {"he": "חולצה קלאסית", "en": "Classic T-Shirt"},
            "slug": "classic-tshirt",
            "description": {"en": "100% Cotton"},
            "base_price": 25.00,
            "is_active": True,
            "primary_image_url": "https://example.com/images/tshirt1.png",
            "images": ["https://example.com/images/tshirt1.png"],
            "variants": [
                {
                    "id": 50,
                    "sku": "TSHIRT-RED-M",
                    "attributes_json": {"color": "red", "size": "M"},
                    "price_override": 29.99,
                    "stock_quantity": 50
                }
            ],
            "created_at": "2026-08-09T10:00:00Z"
        }
    })

class PaginatedProductResponse(PaginatedResponse):
    data: List[ProductResponse]

class CategoryCreateRequest(BaseModel):
    name: Dict[str, str] = Field(...)
    slug: str = Field(..., pattern="^[a-z0-9-]+$")
    parent_id: Optional[int] = None
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": {"en": "Men's Clothing", "he": "בגדי גברים"},
            "slug": "mens-clothing"
        }
    })

class CategoryResponse(BaseModel):
    id: int
    name: Any
    slug: str
    parent_id: Optional[int] = None

class ProductReviewCreateRequest(BaseModel):
    product_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)

class ProductReviewResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    user_id: int
    customer_name: Optional[str] = None
    rating: int
    comment: Optional[str]
    is_approved: bool
    is_verified_buyer: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PaginatedReviewResponse(PaginatedResponse):
    data: List[ProductReviewResponse]
