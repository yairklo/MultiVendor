from sqlalchemy import Column, Integer, BigInteger, String, Enum, DateTime, ForeignKey, Numeric, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base
from app.db.tenant_scope import TenantScoped

class ShippingMethod(TenantScoped, Base):
    __tablename__ = "shipping_methods"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    free_shipping_threshold = Column(Numeric(10, 2), nullable=True)
    is_active = Column(Boolean, default=True)

class Cart(TenantScoped, Base):
    __tablename__ = "carts"
    id = Column(String(36), primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

class CartItem(TenantScoped, Base):
    __tablename__ = "cart_items"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    cart_id = Column(String(36), ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    variant_id = Column(BigInteger, ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)

    cart = relationship("Cart", back_populates="items")
    variant = relationship("ProductVariant")

class MarketplaceCartItem(Base):
    # A cross-tenant cart is intentionally *not* a single tenant-scoped Cart row
    # (Cart.tenant_id is NOT NULL) -- cart_id here is just a client-generated UUID
    # grouping key, same lazy-create-on-first-add convention as the per-store cart.
    __tablename__ = "marketplace_cart_items"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    cart_id = Column(String(36), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    variant_id = Column(BigInteger, ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=func.now())

    variant = relationship("ProductVariant")

class MasterOrder(Base):
    # Groups the per-tenant sub-orders produced by a single marketplace checkout.
    # Deliberately its own table (not a self-referencing row on `orders`) because
    # a master order has no single tenant_id -- `orders.tenant_id` stays NOT NULL.
    __tablename__ = "master_orders"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    master_order_number = Column(String(50), nullable=False, unique=True)
    total_amount = Column(Numeric(10, 2), nullable=False)
    # One payment covers every sub-order under this master order -- set when
    # PAYMENT_PROVIDER=stripe creates a single PaymentIntent for the whole
    # multi-vendor checkout; the webhook resolves back to this row by it.
    payment_intent_id = Column(String(255), nullable=True, unique=True)
    created_at = Column(DateTime, default=func.now())

    sub_orders = relationship("Order", back_populates="master_order")

class Order(TenantScoped, Base):
    __tablename__ = "orders"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    coupon_id = Column(BigInteger, ForeignKey("coupons.id", ondelete="SET NULL"), nullable=True)
    # Set only for sub-orders spawned by a marketplace checkout; NULL for a normal
    # single-store checkout via /api/v1/store/{tenant_slug}/cart/checkout.
    master_order_id = Column(BigInteger, ForeignKey("master_orders.id", ondelete="SET NULL"), nullable=True)
    order_number = Column(String(50), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    discount_amt = Column(Numeric(10, 2), default=0.00)
    shipping_method_id = Column(BigInteger, ForeignKey("shipping_methods.id", ondelete="SET NULL"), nullable=True)
    shipping_fee = Column(Numeric(10, 2), default=0.00)
    total_amount = Column(Numeric(10, 2), nullable=False)
    # Vendor-facing split of total_amount for marketplace sub-orders (0.00 for
    # normal single-store orders): what the platform keeps vs. what the vendor is owed.
    platform_commission = Column(Numeric(10, 2), nullable=False, default=0.00)
    vendor_net_payout = Column(Numeric(10, 2), nullable=False, default=0.00)
    # 'shipped' sits between 'processing' and 'completed': set by
    # fulfill_order_service once a courier has actually accepted the
    # shipment (tracking_number populated), not just when the vendor clicks
    # "Fulfill" -- see app/services/shipping_service.py.
    status = Column(Enum('pending', 'pending_payment', 'processing', 'shipped', 'completed', 'cancelled', 'expired'), default='pending')
    order_type = Column(Enum('physical', 'digital'), default='physical')
    shipping_json = Column(JSON, nullable=True)
    # Set when PAYMENT_PROVIDER=stripe creates a PaymentIntent for this
    # (single-store) order; NULL for mock-mode orders and for marketplace
    # sub-orders, which are paid via MasterOrder.payment_intent_id instead.
    payment_intent_id = Column(String(255), nullable=True, unique=True)
    # Populated by fulfill_order_service (app/services/shipping_service.py)
    # after a successful israel_shipping_sdk create_shipment call. All NULL
    # until fulfilled; shipping_provider mirrors israel_shipping_sdk's
    # ProviderCode values ('hfd' / 'lionwheel'), not TenantShippingConfig.id,
    # so it stays meaningful even if the tenant later deletes that config row.
    tracking_number = Column(String(255), nullable=True)
    shipping_label_url = Column(String(512), nullable=True)
    shipping_provider = Column(Enum('hfd', 'lionwheel'), nullable=True)
    shipped_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    master_order = relationship("MasterOrder", back_populates="sub_orders")

class OrderItem(TenantScoped, Base):
    __tablename__ = "order_items"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    order_id = Column(BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    variant_id = Column(BigInteger, ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)
    product_name = Column(String(255), nullable=False)
    sku = Column(String(100), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False)
    
    order = relationship("Order", back_populates="items")
