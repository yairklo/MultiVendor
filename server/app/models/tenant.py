from sqlalchemy import Column, Integer, BigInteger, String, Enum, DateTime, ForeignKey, Numeric, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    price_monthly = Column(Numeric(10, 2), nullable=False, default=0.00)
    max_products = Column(Integer, nullable=False, default=50)
    max_storage_mb = Column(Integer, nullable=False, default=500)
    features_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    tenants = relationship("Tenant", back_populates="plan")

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(100), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"), nullable=False)
    status = Column(Enum('active', 'suspended', 'cancelled'), nullable=False, default='active')
    custom_domain = Column(String(255), nullable=True, unique=True)
    # Coarse marketplace opt-in: when true, every active product of this tenant is
    # eligible for the cross-store marketplace listing unless overridden per-product
    # (see Product.show_in_marketplace in models/catalog.py).
    show_all_products_in_marketplace = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    plan = relationship("SubscriptionPlan", back_populates="tenants")
    memberships = relationship("UserStoreMembership", back_populates="tenant", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="tenant", cascade="all, delete-orphan")
    settings = relationship("TenantSettings", back_populates="tenant", uselist=False, cascade="all, delete-orphan")

class TenantSettings(Base):
    __tablename__ = "tenant_settings"
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    logo_url = Column(Text, nullable=True)
    primary_color = Column(String(20), default="#000000")
    banner_url = Column(Text, nullable=True)
    currency = Column(String(3), default="ILS")
    custom_css = Column(Text, nullable=True)
    support_email = Column(String(255), nullable=True)
    supported_languages = Column(JSON, nullable=True)
    default_language = Column(String(10), default="he")
    review_moderation_enabled = Column(Boolean, default=False)
    allow_unverified_reviews = Column(Boolean, default=True)
    # Which of the 3 premium storefront templates (see storefront_templates.py) this seller last
    # applied — NULL until they pick one. Purely informational for the admin UI; applying a
    # template doesn't require this to already be set, it just stamps it going forward.
    template_key = Column(String(50), nullable=True)
    draft_template_key = Column(String(50), nullable=True)

    tenant = relationship("Tenant", back_populates="settings")
