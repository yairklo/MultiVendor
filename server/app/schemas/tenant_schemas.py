from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
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
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "store_name": "Nike Israel",
            "store_slug": "nike-israel",
            "admin_email": "owner@nike.co.il",
            "admin_password": "securePassword123!",
            "admin_full_name": "Nike Owner",
            "plan_code": "pro"
        }
    })

class TenantUpdateSchema(BaseModel):
    custom_domain: Optional[str] = None

class TenantSettingsSchema(BaseModel):
    logo_url: Optional[str] = None
    primary_color: str = "#000000"
    banner_url: Optional[str] = None
    currency: str = "ILS"
    custom_css: Optional[str] = None
    support_email: Optional[EmailStr] = None
    supported_languages: List[str] = ["he"]
    default_language: str = "he"
    review_moderation_enabled: bool = False
    allow_unverified_reviews: bool = True

    @field_validator('supported_languages', mode='before')
    @classmethod
    def _default_supported_languages(cls, v):
        # The column is nullable (rows created before a store ever configured
        # languages), so a stored NULL means "not set" — fall back to the
        # same default new settings get, rather than failing validation.
        return v if v else ["he"]

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "logo_url": "https://example.com/logo.png",
            "primary_color": "#FF0000",
            "banner_url": "https://example.com/banner.png",
            "currency": "ILS",
            "custom_css": "body { font-family: Arial; }",
            "support_email": "support@nike.co.il",
            "supported_languages": ["he", "en"],
            "default_language": "he",
            "review_moderation_enabled": False,
            "allow_unverified_reviews": True
        }
    }, from_attributes=True)

class TenantResponse(BaseModel):
    id: int
    slug: str
    name: str
    plan_code: PlanCode
    status: str
    created_at: datetime
    custom_domain: Optional[str] = None
    settings: Optional[TenantSettingsSchema] = None
    model_config = ConfigDict(from_attributes=True)

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
