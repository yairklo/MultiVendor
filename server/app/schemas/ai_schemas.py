from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field

SectionType = Literal[
    "hero_banner", "product_grid", "video_embed", "text_block", "gallery", "button_group", "table",
    "grid_container", "two_column_layout",
]
PageType = Literal["static_page", "template"]
MediaType = Literal["image", "video"]
ButtonVariant = Literal["primary", "secondary", "outline"]
ButtonActionType = Literal["NAVIGATE", "OPEN_MODAL", "ADD_TO_CART", "APPLY_COUPON"]
DesignVariant = Literal["primary", "accent", "secondary", "muted", "neutral"]

SECTION_TYPES: tuple = (
    "hero_banner", "product_grid", "video_embed", "text_block", "gallery", "button_group", "table",
    "grid_container", "two_column_layout",
)
BUTTON_ACTION_TYPES: tuple = ("NAVIGATE", "OPEN_MODAL", "ADD_TO_CART", "APPLY_COUPON")
BUTTON_VARIANTS: tuple = ("primary", "secondary", "outline")
# Structural sections that hold other sections rather than rendering leaf content themselves.
CONTAINER_SECTION_TYPES: tuple = ("grid_container", "two_column_layout")
# AI-selectable Tailwind design tokens for container theming (frontend/src/lib/design-tokens.ts
# maps each to a literal, statically-scanned class string) — kept separate from the free-text
# background_color/text_color path the original 7 section types use.
DESIGN_VARIANTS: tuple = ("primary", "accent", "secondary", "muted", "neutral")
# A store's page tree is user/AI-authored — cap nesting so a hallucinated or malicious payload
# can't produce pathologically deep recursion server- or client-side.
MAX_SECTION_NESTING_DEPTH = 3

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
    page_key: str = Field(..., min_length=1)
    page_type: PageType

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

class CustomerInsightsResponse(BaseModel):
    total_customers: int
    customers_with_orders: int
    repeat_customer_rate: float
    top_spenders: List[Dict[str, Any]]
    recent_signups: List[Dict[str, Any]]
