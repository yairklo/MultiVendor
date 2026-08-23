from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey, Numeric, Text, JSON, CheckConstraint, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base
from app.db.tenant_scope import TenantScoped

class Category(TenantScoped, Base):
    __tablename__ = "categories"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(BigInteger, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    name = Column(JSON, nullable=False)
    slug = Column(String(100), nullable=False)

class Product(TenantScoped, Base):
    __tablename__ = "products"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(BigInteger, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    name = Column(JSON, nullable=False)
    slug = Column(String(255), nullable=False)
    description = Column(JSON, nullable=True)
    base_price = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, default=True)
    # Per-product marketplace opt-in, independent of Tenant.show_all_products_in_marketplace
    # (a store-wide opt-out can still be overridden product-by-product).
    show_in_marketplace = Column(Boolean, nullable=False, default=False)
    product_type = Column(Enum('physical', 'digital', 'service'), default='physical')
    digital_file_url = Column(String(512), nullable=True)
    download_limit = Column(Integer, nullable=True)
    is_bundle = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    
    tenant = relationship("Tenant", back_populates="products")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    reviews = relationship("ProductReview", back_populates="product", cascade="all, delete-orphan")

class ProductVariant(TenantScoped, Base):
    __tablename__ = "product_variants"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    sku = Column(String(100), nullable=False)
    attributes_json = Column(JSON, nullable=True)
    price_override = Column(Numeric(10, 2), nullable=True)
    stock_quantity = Column(Integer, nullable=False, default=0)

    product = relationship("Product", back_populates="variants")

class ProductImage(TenantScoped, Base):
    __tablename__ = "product_images"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    image_url = Column(Text, nullable=False)
    is_primary = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)

    product = relationship("Product", back_populates="images")

class ProductReview(TenantScoped, Base):
    __tablename__ = "product_reviews"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, CheckConstraint('rating BETWEEN 1 AND 5'), nullable=False)
    comment = Column(Text, nullable=True)
    is_approved = Column(Boolean, default=True)
    is_verified_buyer = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    product = relationship("Product", back_populates="reviews")

class ProductBundleItem(Base):
    __tablename__ = "product_bundle_items"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    bundle_product_id = Column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    component_variant_id = Column(BigInteger, ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
