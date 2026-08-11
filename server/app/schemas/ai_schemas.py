from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, ConfigDict, Field

SectionType = Literal[
    "hero_banner", "product_grid", "video_embed", "text_block", "gallery", "button_group", "table"
]
PageType = Literal["static_page", "template"]
MediaType = Literal["image", "video"]
ButtonVariant = Literal["primary", "secondary", "outline"]
ButtonActionType = Literal["NAVIGATE", "OPEN_MODAL", "ADD_TO_CART", "APPLY_COUPON"]

SECTION_TYPES: tuple = ("hero_banner", "product_grid", "video_embed", "text_block", "gallery", "button_group", "table")
BUTTON_ACTION_TYPES: tuple = ("NAVIGATE", "OPEN_MODAL", "ADD_TO_CART", "APPLY_COUPON")
BUTTON_VARIANTS: tuple = ("primary", "secondary", "outline")

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
    model_config = ConfigDict(from_attributes=True)

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

class AIChatResponse(BaseModel):
    reply: str
    tool_calls: List[ToolCallRecord]
    used_provider: Literal["gemini", "mock"]
    page: Optional[StorePageSchema] = None

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
