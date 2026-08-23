from sqlalchemy import Column, BigInteger, Integer, String, Enum, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base
from app.db.tenant_scope import TenantScoped

class StorePage(TenantScoped, Base):
    __tablename__ = "store_pages"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    page_key = Column(String(100), nullable=False)
    page_type = Column(Enum('static_page', 'template'), nullable=False, default='static_page')
    title = Column(String(255), nullable=False)
    sections = Column(JSON, nullable=False)
    # Page-level theme, distinct from a section's own settings.background_color —
    # this is what actually shows in the margins/gaps around and between
    # sections, not just inside one section's card.
    background_color = Column(String(20), nullable=True)
    text_color = Column(String(20), nullable=True)
    # `sections`/`title`/`background_color`/`text_color` above are the DRAFT —
    # what the AI and the admin preview read/write. The public storefront never
    # reads them directly; it only ever sees the snapshot below, which only
    # changes when the store owner explicitly publishes.
    published_sections = Column(JSON, nullable=True)
    published_title = Column(String(255), nullable=True)
    published_background_color = Column(String(20), nullable=True)
    published_text_color = Column(String(20), nullable=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "page_key", "page_type", name="uq_store_pages_tenant_key_type"),
    )

    tenant = relationship("Tenant")


class StorePageVersion(TenantScoped, Base):
    __tablename__ = "store_page_versions"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    store_page_id = Column(BigInteger, ForeignKey("store_pages.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    page_key = Column(String(100), nullable=False)
    page_type = Column(Enum('static_page', 'template'), nullable=False)
    title = Column(String(255), nullable=False)
    sections = Column(JSON, nullable=False)
    background_color = Column(String(20), nullable=True)
    text_color = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=func.now())


class AIConversation(TenantScoped, Base):
    __tablename__ = "ai_conversations"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    # Both NULL together means the tenant-wide global copilot conversation, not
    # tied to any real page — never a fake page_key like 'global'. A real page's
    # conversation always has both set.
    page_key = Column(String(100), nullable=True)
    page_type = Column(Enum('static_page', 'template'), nullable=True)
    # Serialized google.genai Content[] for real multi-turn continuity — never
    # read by the AI itself, only round-tripped through the Gemini SDK.
    gemini_history = Column(JSON, nullable=True)
    # Display transcript ({role, text, tool_calls}[]) so reopening a page shows
    # what was actually shown before, not just what the model still remembers.
    messages = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_id", "page_key", "page_type", name="uq_ai_conversations_tenant_key_type"),
    )
