from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal
from app.schemas.common_schemas import PaginatedResponse, ReviewStatus

class ProductVariantSchema(BaseModel):
    id: Optional[int] = None
    sku: str
    attributes_json: Dict[str, Any]
    price_override: Optional[Decimal] = None
    stock_quantity: int = Field(..., ge=0)

class ProductCreateRequest(BaseModel):
    category_id: Optional[int] = None
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., pattern="^[a-z0-9-]+$")
    description: Optional[str] = None
    base_price: Decimal = Field(..., gt=0)
    is_active: bool = True
    variants: List[ProductVariantSchema]
    images: List[str]

class ProductUpdateRequest(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    base_price: Optional[Decimal] = Field(None, gt=0)
    is_active: Optional[bool] = None

class ProductResponse(BaseModel):
    id: int
    tenant_id: int
    category_id: Optional[int]
    name: str
    slug: str
    description: Optional[str]
    base_price: Decimal
    is_active: bool
    variants: List[ProductVariantSchema]
    primary_image_url: Optional[str]
    images: List[str]
    created_at: datetime

class PaginatedProductResponse(PaginatedResponse):
    data: List[ProductResponse]

class CategoryCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., pattern="^[a-z0-9-]+$")
    parent_id: Optional[int] = None

class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    parent_id: Optional[int] = None

class ProductReviewCreateRequest(BaseModel):
    product_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)

class ProductReviewResponse(BaseModel):
    id: int
    product_id: int
    user_id: int
    rating: int
    comment: Optional[str]
    status: ReviewStatus
    created_at: datetime

class PaginatedReviewResponse(PaginatedResponse):
    data: List[ProductReviewResponse]
