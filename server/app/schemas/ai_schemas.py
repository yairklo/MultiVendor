from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

SectionType = Literal[
    "hero_banner", "product_grid", "video_embed", "text_block", "gallery", "button_group", "table",
    "grid_container", "two_column_layout", "feature_highlights", "testimonials",
]
PageType = Literal["static_page", "template"]
MediaType = Literal["image", "video"]
ButtonVariant = Literal["primary", "secondary", "outline"]
ButtonActionType = Literal["NAVIGATE", "OPEN_MODAL", "ADD_TO_CART", "APPLY_COUPON"]
DesignVariant = Literal["primary", "accent", "secondary", "muted", "neutral"]
CardStyle = Literal["default", "framed", "minimal"]

SECTION_TYPES: tuple = (
    "hero_banner", "product_grid", "video_embed", "text_block", "gallery", "button_group", "table",
    "grid_container", "two_column_layout", "feature_highlights", "testimonials",
)
BUTTON_ACTION_TYPES: tuple = ("NAVIGATE", "OPEN_MODAL", "ADD_TO_CART", "APPLY_COUPON")
BUTTON_VARIANTS: tuple = ("primary", "secondary", "outline")
# Structural sections that hold other sections rather than rendering leaf content themselves.
CONTAINER_SECTION_TYPES: tuple = ("grid_container", "two_column_layout")
# AI-selectable Tailwind design tokens for container theming (frontend/src/lib/design-tokens.ts
# maps each to a literal, statically-scanned class string) — kept separate from the free-text
# background_color/text_color path the original 7 section types use.
DESIGN_VARIANTS: tuple = ("primary", "accent", "secondary", "muted", "neutral")
# AI-selectable product card presentation for product_grid sections (frontend/src/lib/
# product-card-styles.ts maps each to a literal, statically-scanned class string) — lets the AI
# restyle how product cards look without ever touching the card's markup or its Add to Cart wiring.
CARD_STYLES: tuple = ("default", "framed", "minimal")
# A store's page tree is user/AI-authored — cap nesting so a hallucinated or malicious payload
# can't produce pathologically deep recursion server- or client-side.
MAX_SECTION_NESTING_DEPTH = 3


def _utc_iso(value: Optional[datetime]) -> Optional[str]:
    """
    MySQL TIMESTAMP columns round-trip as naive datetimes representing the
    session's clock (UTC here), but a bare `datetime.isoformat()` omits the
    offset — browsers then parse it as local time, skewing every "time ago"
    display by the client's UTC offset. Stamp it explicitly as UTC instead.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()

class SectionMedia(BaseModel):
    type: MediaType
    url: str
    aspect_ratio: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class Section(BaseModel):
    id: Optional[str] = None
    type: SectionType
    settings: Dict[str, Any] = Field(default_factory=dict)
    media: Optional[SectionMedia] = None
    # Only meaningful for type="grid_container" — the sections rendered inside the grid.
    children: Optional[List["Section"]] = None
    # Only meaningful for type="two_column_layout" — keys are "left"/"right".
    zones: Optional[Dict[str, List["Section"]]] = None
    model_config = ConfigDict(from_attributes=True)


Section.model_rebuild()

class StorePageSchema(BaseModel):
    page_key: str
    page_type: PageType
    title: str
    sections: List[Section]
    # Page-level theme — what shows in the margins/gaps around and between
    # sections. Distinct from any single section's own settings.background_color.
    background_color: Optional[str] = None
    text_color: Optional[str] = None
    # Only meaningful for the admin/draft view (always False on the published
    # copy the public storefront reads) — True means there are edits the store
    # owner hasn't published yet.
    has_unpublished_changes: bool = False
    published_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("published_at")
    def _serialize_published_at(self, value: Optional[datetime]) -> Optional[str]:
        return _utc_iso(value)

class SavePageSectionsRequest(BaseModel):
    """Direct write path for the drag-and-drop editor — bypasses the AI/Gemini tool-calling
    loop entirely, but is validated by the exact same recursive sanitizer as an AI-authored
    update_page_sections call, so a manually-dragged payload gets identical guarantees."""
    page_key: str = Field(..., min_length=1)
    page_type: PageType
    sections: List[Section]
    title: Optional[str] = None
    background_color: Optional[str] = None
    text_color: Optional[str] = None

class StorePageSummary(BaseModel):
    page_key: str
    page_type: PageType
    title: str
    section_count: int

class AIChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    # None means "the tenant-wide global copilot conversation" — not tied to any
    # real page. A real page's conversation must supply both; never just one.
    page_key: Optional[str] = Field(None, min_length=1)
    page_type: Optional[PageType] = None

    @model_validator(mode="after")
    def _page_key_and_type_together(self) -> "AIChatRequest":
        if (self.page_key is None) != (self.page_type is None):
            raise ValueError("page_key and page_type must both be provided or both omitted")
        return self

class ToolCallRecord(BaseModel):
    name: str
    input: Any
    output: Any
    is_error: bool

class PendingConfirmation(BaseModel):
    id: str
    tool_name: str
    summary: str

class AIChatResponse(BaseModel):
    reply: str
    tool_calls: List[ToolCallRecord]
    used_provider: Literal["gemini", "mock"]
    page: Optional[StorePageSchema] = None
    pending_confirmation: Optional[PendingConfirmation] = None

class AIStatusResponse(BaseModel):
    provider: Literal["gemini", "mock"]

class StorePageVersionSummary(BaseModel):
    id: int
    created_at: datetime
    title: str
    section_count: int
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def _serialize_created_at(self, value: datetime) -> Optional[str]:
        return _utc_iso(value)

class ChatMessageRecord(BaseModel):
    role: Literal["user", "assistant"]
    text: str
    tool_calls: Optional[List[ToolCallRecord]] = None

class ConversationResponse(BaseModel):
    messages: List[ChatMessageRecord]

class InventoryHealthItem(BaseModel):
    product_id: int
    product_name: Any
    variant_id: int
    sku: str
    stock_quantity: int

class InventoryHealthResponse(BaseModel):
    low_stock_threshold: int
    out_of_stock: List[InventoryHealthItem]
    low_stock: List[InventoryHealthItem]

class TopSellingProduct(BaseModel):
    # order_items snapshots sku/product_name at sale time rather than an FK to
    # products (variant_id is even nullable, SET NULL if the variant is later
    # deleted) — sku is the stable, always-present identifier to group by.
    sku: str
    product_name: str
    quantity_sold: int
    revenue: float

class SalesAnalyticsResponse(BaseModel):
    start_date: str
    end_date: str
    total_revenue: float
    orders_count: int
    aov: float
    daily: List[Dict[str, Any]]
    top_selling_products: List[TopSellingProduct]

class StorefrontTemplateSummary(BaseModel):
    key: str
    name: str
    tagline: str
    swatch: Dict[str, str]

class ApplyStorefrontTemplateResponse(BaseModel):
    template_key: str
    pages: List[StorePageSchema]

class CustomerInsightsResponse(BaseModel):
    total_customers: int
    customers_with_orders: int
    repeat_customer_rate: float
    top_spenders: List[Dict[str, Any]]
    recent_signups: List[Dict[str, Any]]
