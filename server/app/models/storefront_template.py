from sqlalchemy import Column, Integer, String, JSON, Boolean, DateTime
from sqlalchemy.sql import func
from app.db.base_class import Base

class StorefrontTemplate(Base):
    # Global reference content (like SubscriptionPlan), not TenantScoped --
    # every tenant browses the same catalog of templates. Moved out of
    # storefront_templates.py's static Python list so a new template (or an
    # edit to an existing one) is a DB write, not a code change + deploy; the
    # 3 built-in templates that ship with the app are still defined in
    # Python there and seeded into this table by migration 0002.
    __tablename__ = "storefront_templates"
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_key = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    tagline = Column(String(255), nullable=False)
    swatch_json = Column(JSON, nullable=False)
    pages_json = Column(JSON, nullable=False)
    display_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
