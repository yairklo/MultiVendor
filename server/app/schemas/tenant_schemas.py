from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from decimal import Decimal
from app.schemas.common_schemas import PlanCode, PaginatedResponse

class TenantRegisterRequest(BaseModel):
    store_name: str = Field(..., min_length=3, max_length=100)
    store_slug: str = Field(..., min_length=2, max_length=50, pattern="^[a-z0-9-]+$")
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8)
    admin_full_name: str
    plan_code: PlanCode = PlanCode.FREE

class TenantSettingsSchema(BaseModel):
    logo_url: Optional[str] = None
    primary_color: str = "#000000"
    banner_url: Optional[str] = None
    currency: str = "ILS"
    custom_css: Optional[str] = None
    support_email: Optional[EmailStr] = None

class TenantResponse(BaseModel):
    id: int
    slug: str
    name: str
    plan_code: PlanCode
    status: str
    created_at: datetime
    settings: Optional[TenantSettingsSchema] = None

class PaginatedTenantResponse(PaginatedResponse):
    data: List[TenantResponse]

class SubscriptionPlanResponse(BaseModel):
    id: int
    code: PlanCode
    name: str
    price_monthly: Decimal
    max_products: int
    max_storage_mb: int
    features_json: Dict[str, Any]
