from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator, model_validator
from datetime import datetime
from decimal import Decimal
from app.schemas.common_schemas import PlanCode, PaginatedResponse
from app.services.i18n_utils import LANG_CODE_RE, validate_language_codes
from app.schemas.catalog_schemas import normalize_asset_url

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

class TenantMarketplaceVisibilityUpdateSchema(BaseModel):
    show_all_products_in_marketplace: bool

class NavItemSchema(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    enabled: bool = True
    kind: Literal["home", "shop", "marketplace", "page", "custom"] = "page"
    page_key: Optional[str] = Field(None, max_length=100)
    href: Optional[str] = Field(None, max_length=500)
    label: Dict[str, str] = Field(default_factory=dict)

    @field_validator("href")
    @classmethod
    def _safe_href(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        lowered = v.strip()
        if lowered.lower().startswith(("javascript:", "data:")) or lowered.startswith("//"):
            raise ValueError("Invalid href")
        if lowered.startswith(("https://", "http://", "/", "mailto:")):
            return lowered
        raise ValueError("href must be a relative path or http(s) URL")

    @model_validator(mode="after")
    def _kind_fields(self):
        if self.kind == "page" and not self.page_key:
            raise ValueError("page_key is required for page nav items")
        if self.kind == "custom" and not self.href:
            raise ValueError("href is required for custom nav items")
        return self


class TenantSettingsUpdateSchema(BaseModel):
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    banner_url: Optional[str] = None
    currency: Optional[str] = None
    custom_css: Optional[str] = None
    support_email: Optional[EmailStr] = None
    supported_languages: Optional[List[str]] = None
    default_language: Optional[str] = None
    review_moderation_enabled: Optional[bool] = None
    allow_unverified_reviews: Optional[bool] = None
    template_key: Optional[str] = None
    nav_items: Optional[List[NavItemSchema]] = None

    @field_validator("logo_url", "banner_url")
    @classmethod
    def _safe_asset_url(cls, v: Optional[str]) -> Optional[str]:
        return normalize_asset_url(v, field_name="url", allow_empty=True)

    @field_validator("supported_languages")
    @classmethod
    def _validate_langs(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            validate_language_codes(v)
        return v

    @field_validator("default_language")
    @classmethod
    def _validate_default_lang(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not LANG_CODE_RE.match(v):
            raise ValueError(f"Invalid language code: {v}")
        return v

    @model_validator(mode="after")
    def _default_in_supported(self):
        if self.default_language and self.supported_languages:
            if self.default_language not in self.supported_languages:
                raise ValueError("default_language must be one of supported_languages")
        return self


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
    template_key: Optional[str] = None
    nav_items: Optional[List[NavItemSchema]] = None

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
    show_all_products_in_marketplace: bool = False
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

class SubscriptionPlanInfo(BaseModel):
    plan_code: PlanCode
    max_products: int
    max_storage_mb: int

class DailySalesPoint(BaseModel):
    date: Optional[str] = None
    total_sales: float
    order_count: int

class TenantAnalyticsResponse(BaseModel):
    data: List[DailySalesPoint]
    total_revenue: float
    orders_count: int
    aov: float
