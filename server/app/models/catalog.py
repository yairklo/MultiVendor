from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey, Numeric, Text, JSON, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

class Category(Base):
    __tablename__ = "categories"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(BigInteger, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False)

class Product(Base):
    __tablename__ = "products"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(BigInteger, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    base_price = Column(Numeric(10, 2), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    tenant = relationship("Tenant", back_populates="products")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    reviews = relationship("ProductReview", back_populates="product", cascade="all, delete-orphan")

class ProductVariant(Base):
    __tablename__ = "product_variants"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    sku = Column(String(100), nullable=False)
    attributes_json = Column(JSON, nullable=True)
    price_override = Column(Numeric(10, 2), nullable=True)
    stock_quantity = Column(Integer, nullable=False, default=0)

    product = relationship("Product", back_populates="variants")

class ProductImage(Base):
    __tablename__ = "product_images"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    image_url = Column(Text, nullable=False)
    is_primary = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)

    product = relationship("Product", back_populates="images")

class ProductReview(Base):
    __tablename__ = "product_reviews"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, CheckConstraint('rating BETWEEN 1 AND 5'), nullable=False)
    comment = Column(Text, nullable=True)
    approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

    product = relationship("Product", back_populates="reviews")
