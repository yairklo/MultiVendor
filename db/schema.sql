-- ================================================================================
-- DATABASE CREATION & CONFIGURATION
-- ================================================================================
CREATE DATABASE IF NOT EXISTS multivendor_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE multivendor_dev;

-- ================================================================================
-- 1. SUBSCRIPTIONS & TENANTS LAYER
-- ================================================================================
CREATE TABLE subscription_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    price_monthly DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    max_products INT NOT NULL DEFAULT 50,
    max_storage_mb INT NOT NULL DEFAULT 500,
    features_json JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE tenants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    slug VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    plan_id INT NOT NULL,
    status ENUM('active', 'suspended', 'cancelled') NOT NULL DEFAULT 'active',
    custom_domain VARCHAR(255) UNIQUE NULL,
    -- Coarse marketplace opt-in: TRUE exposes every active product of this
    -- tenant on the cross-store marketplace, unless a product overrides it
    -- (see products.show_in_marketplace below).
    show_all_products_in_marketplace BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (plan_id) REFERENCES subscription_plans(id)
) ENGINE=InnoDB;

CREATE TABLE tenant_settings (
    tenant_id INT PRIMARY KEY,
    logo_url TEXT NULL,
    primary_color VARCHAR(20) DEFAULT '#000000',
    banner_url TEXT NULL,
    currency VARCHAR(3) DEFAULT 'ILS',
    custom_css TEXT NULL,
    support_email VARCHAR(255) NULL,
    supported_languages JSON NULL,
    default_language VARCHAR(10) DEFAULT 'he',
    review_moderation_enabled BOOLEAN DEFAULT FALSE,
    allow_unverified_reviews BOOLEAN DEFAULT TRUE,
    template_key VARCHAR(50) NULL,
    draft_template_key VARCHAR(50) NULL,
    nav_items JSON NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE tenant_billing_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status ENUM('paid', 'failed', 'pending') NOT NULL,
    invoice_url TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- One row per (tenant, courier) a vendor has connected -- see
-- app/services/shipping_service.py and app/core/crypto.py. credentials_encrypted
-- is a Fernet-encrypted JSON blob whose shape depends on `provider`, kept as one
-- encrypted column rather than provider-specific plaintext columns so a third
-- courier never needs a schema migration for its own credential shape.
-- sender_* is the pickup address every courier shipment needs as its "from"
-- -- there is nowhere else in this schema with a store phone/address at
-- all, and a courier account is issued against one pickup location, so this
-- is the correct scope for it rather than a new platform-wide concept.
CREATE TABLE tenant_shipping_configs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    provider ENUM('hfd', 'lionwheel') NOT NULL,
    credentials_encrypted TEXT NOT NULL,
    sender_name VARCHAR(255) NOT NULL,
    sender_phone VARCHAR(20) NOT NULL,
    sender_city VARCHAR(100) NOT NULL,
    sender_street VARCHAR(255) NOT NULL,
    sender_house_number VARCHAR(20) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    -- When true, an order is dispatched to this courier automatically the
    -- moment it's marked 'processing' -- see
    -- shipping_service.maybe_auto_fulfill_order. Off by default.
    auto_fulfill BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT uq_tenant_shipping_provider UNIQUE (tenant_id, provider)
) ENGINE=InnoDB;

-- ================================================================================
-- 2. USERS & SECURITY LAYER
-- ================================================================================
-- Identity is global: one row per person/email across the entire platform, not
-- per store. `role` only distinguishes the platform super_admin from every
-- regular account -- store-level roles (tenant_admin / customer) live on
-- user_store_memberships below, since the same person can be a tenant_admin
-- of one store and a customer of another.
CREATE TABLE users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role ENUM('super_admin', 'user') NOT NULL DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- A user's role and standing at one specific store. Rows are created either
-- explicitly (POST .../auth/register-customer/{tenant_slug}, tenant creation)
-- or lazily the first time a global user acts as a customer at a store they
-- haven't shopped at before (see deps.get_tenant_customer) -- never lazily for
-- tenant_admin, which would be a privilege-escalation hole.
CREATE TABLE user_store_memberships (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    tenant_id INT NOT NULL,
    role ENUM('tenant_admin', 'customer') NOT NULL DEFAULT 'customer',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_tenant UNIQUE (user_id, tenant_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE audit_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NULL,
    user_id BIGINT NULL,
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(100) NOT NULL,
    ip_address VARCHAR(45) NULL,
    details_json JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ================================================================================
-- 3. CATALOG & INVENTORY LAYER
-- ================================================================================
CREATE TABLE categories (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    parent_id BIGINT NULL,
    name JSON NOT NULL,
    slug VARCHAR(100) NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL,
    CONSTRAINT uq_categories_tenant_slug UNIQUE (tenant_id, slug)
) ENGINE=InnoDB;

CREATE TABLE products (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    category_id BIGINT NULL,
    name JSON NOT NULL,
    slug VARCHAR(255) NOT NULL,
    description JSON NULL,
    base_price DECIMAL(10, 2) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    -- Per-product marketplace opt-in, independent of (and able to override)
    -- tenants.show_all_products_in_marketplace.
    show_in_marketplace BOOLEAN NOT NULL DEFAULT FALSE,
    product_type ENUM('physical', 'digital', 'service') DEFAULT 'physical',
    digital_file_url VARCHAR(512) NULL,
    download_limit INT NULL,
    is_bundle BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
    CONSTRAINT uq_products_tenant_slug UNIQUE (tenant_id, slug)
) ENGINE=InnoDB;

CREATE TABLE product_variants (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    product_id BIGINT NOT NULL,
    sku VARCHAR(100) NOT NULL,
    attributes_json JSON NULL, -- e.g. {"color": "red", "size": "XL"}
    price_override DECIMAL(10, 2) NULL,
    stock_quantity INT NOT NULL DEFAULT 0,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    CONSTRAINT uq_variants_tenant_sku UNIQUE (tenant_id, sku)
) ENGINE=InnoDB;

CREATE TABLE product_images (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    product_id BIGINT NOT NULL,
    image_url TEXT NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE,
    sort_order INT DEFAULT 0,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE product_reviews (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    product_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT NULL,
    is_approved BOOLEAN DEFAULT TRUE,
    is_verified_buyer BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE product_bundle_items (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    bundle_product_id BIGINT NOT NULL,
    component_variant_id BIGINT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    FOREIGN KEY (bundle_product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (component_variant_id) REFERENCES product_variants(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ================================================================================
-- 4. CART, PROMOTIONS & ORDERS LAYER
-- ================================================================================
CREATE TABLE coupons (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    code VARCHAR(50) NOT NULL,
    discount_type ENUM('percentage', 'fixed') NOT NULL,
    discount_val DECIMAL(10, 2) NOT NULL,
    min_order_amt DECIMAL(10, 2) DEFAULT 0.00,
    usage_limit INT DEFAULT 0,
    used_count INT DEFAULT 0,
    valid_until TIMESTAMP NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT uq_coupons_tenant_code UNIQUE (tenant_id, code)
) ENGINE=InnoDB;

CREATE TABLE shipping_methods (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    free_shipping_threshold DECIMAL(10, 2) NULL,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE carts (
    id VARCHAR(36) PRIMARY KEY, -- UUID
    tenant_id INT NOT NULL,
    user_id BIGINT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE cart_items (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    cart_id VARCHAR(36) NOT NULL,
    variant_id BIGINT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- A cross-tenant marketplace cart is NOT a `carts` row (carts.tenant_id is
-- NOT NULL, by design, for the single-store cart). cart_id is just a
-- client-generated UUID grouping key, same lazy-create-on-first-add
-- convention as cart_items, spanning multiple tenant_ids at once.
CREATE TABLE marketplace_cart_items (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    cart_id VARCHAR(36) NOT NULL,
    tenant_id INT NOT NULL,
    variant_id BIGINT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE INDEX idx_marketplace_cart_items_cart ON marketplace_cart_items(cart_id);

-- Groups the per-tenant sub-orders produced by one marketplace checkout. Its
-- own table (not a self-referencing row on `orders`) because a master order
-- has no single tenant_id -- orders.tenant_id stays NOT NULL.
CREATE TABLE master_orders (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    master_order_number VARCHAR(50) NOT NULL UNIQUE,
    total_amount DECIMAL(10, 2) NOT NULL,
    -- One payment (a single Stripe PaymentIntent) covers every sub-order
    -- under this master order; NULL in mock-payment mode.
    payment_intent_id VARCHAR(255) NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE orders (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    user_id BIGINT NOT NULL,
    coupon_id BIGINT NULL,
    -- Set only for sub-orders spawned by a marketplace checkout; NULL for a
    -- normal single-store checkout.
    master_order_id BIGINT NULL,
    order_number VARCHAR(50) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,
    discount_amt DECIMAL(10, 2) DEFAULT 0.00,
    shipping_method_id BIGINT NULL,
    shipping_fee DECIMAL(10, 2) DEFAULT 0.00,
    total_amount DECIMAL(10, 2) NOT NULL,
    -- Vendor-facing split of total_amount for marketplace sub-orders (both
    -- 0.00 for a normal single-store order).
    platform_commission DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    vendor_net_payout DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    -- 'shipped' sits between 'processing' and 'completed': set once a
    -- courier has actually accepted the shipment (tracking_number
    -- populated), not just when the vendor clicks "Fulfill" -- see
    -- app/services/shipping_service.py.
    status ENUM('pending', 'pending_payment', 'processing', 'shipped', 'completed', 'cancelled', 'expired') DEFAULT 'pending',
    order_type ENUM('physical', 'digital') DEFAULT 'physical',
    shipping_json JSON NULL,
    -- Set when PAYMENT_PROVIDER=stripe creates a PaymentIntent for this
    -- (single-store) order; NULL for mock-mode orders and for marketplace
    -- sub-orders, which use master_orders.payment_intent_id instead.
    payment_intent_id VARCHAR(255) NULL UNIQUE,
    -- Populated by fulfill_order_service after a successful
    -- israel_shipping_sdk create_shipment call; all NULL until fulfilled.
    tracking_number VARCHAR(255) NULL,
    shipping_label_url VARCHAR(512) NULL,
    shipping_provider ENUM('hfd', 'lionwheel') NULL,
    shipped_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (coupon_id) REFERENCES coupons(id) ON DELETE SET NULL,
    FOREIGN KEY (master_order_id) REFERENCES master_orders(id) ON DELETE SET NULL,
    FOREIGN KEY (shipping_method_id) REFERENCES shipping_methods(id) ON DELETE SET NULL,
    CONSTRAINT uq_orders_tenant_number UNIQUE (tenant_id, order_number)
) ENGINE=InnoDB;

CREATE TABLE order_items (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    order_id BIGINT NOT NULL,
    variant_id BIGINT NULL,
    product_name VARCHAR(255) NOT NULL, -- Historical Snapshot
    sku VARCHAR(100) NOT NULL,          -- Historical Snapshot
    unit_price DECIMAL(10, 2) NOT NULL, -- Historical Snapshot
    quantity INT NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ================================================================================
-- 5. AI-MANAGED STOREFRONT PAGES
-- ================================================================================
CREATE TABLE store_pages (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    page_key VARCHAR(100) NOT NULL,
    page_type ENUM('static_page', 'template') NOT NULL DEFAULT 'static_page',
    title VARCHAR(255) NOT NULL,
    sections JSON NOT NULL,
    background_color VARCHAR(20) NULL,
    text_color VARCHAR(20) NULL,
    -- Draft columns above are read/written by the AI and the admin preview.
    -- The public storefront only ever reads the published_* snapshot below,
    -- which only changes when the store owner explicitly publishes.
    published_sections JSON NULL,
    published_title VARCHAR(255) NULL,
    published_background_color VARCHAR(20) NULL,
    published_text_color VARCHAR(20) NULL,
    published_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT uq_store_pages_tenant_key_type UNIQUE (tenant_id, page_key, page_type)
) ENGINE=InnoDB;

CREATE TABLE store_page_versions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    store_page_id BIGINT NOT NULL,
    tenant_id INT NOT NULL,
    page_key VARCHAR(100) NOT NULL,
    page_type ENUM('static_page', 'template') NOT NULL,
    title VARCHAR(255) NOT NULL,
    sections JSON NOT NULL,
    background_color VARCHAR(20) NULL,
    text_color VARCHAR(20) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (store_page_id) REFERENCES store_pages(id) ON DELETE CASCADE,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE ai_conversations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    -- Both NULL together = the tenant-wide global copilot conversation, not tied
    -- to any real page (never a fake page_key like 'global'). A real page's
    -- conversation always has both columns set.
    page_key VARCHAR(100) NULL,
    page_type ENUM('static_page', 'template') NULL,
    gemini_history JSON NULL,
    messages JSON NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    -- MySQL's unique index treats every NULL as distinct, so a plain UNIQUE
    -- (tenant_id, page_key, page_type) would NOT stop two concurrent first
    -- messages to the global copilot from each inserting their own
    -- (tenant_id, NULL, NULL) row. These generated columns COALESCE NULL to ''
    -- purely so the unique index below actually enforces "one global thread per
    -- tenant" too — application code never reads or writes them directly.
    page_key_uq VARCHAR(100) AS (COALESCE(page_key, '')) STORED,
    page_type_uq VARCHAR(20) AS (COALESCE(page_type, '')) STORED,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT uq_ai_conversations_tenant_key_type UNIQUE (tenant_id, page_key_uq, page_type_uq)
) ENGINE=InnoDB;

CREATE INDEX idx_store_page_versions_page ON store_page_versions(tenant_id, store_page_id, created_at);

-- Destructive AI-proposed actions (delete_product, cancel an order) never execute
-- directly — they're staged here and only run once a human clicks a real confirm
-- button in the UI (see ai_pending_action_service.py). One-time use: the row is
-- deleted on confirm or cancel, and treated as gone once past expires_at.
CREATE TABLE ai_pending_actions (
    id CHAR(36) PRIMARY KEY,
    tenant_id INT NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    tool_args JSON NOT NULL,
    summary VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Global reference content (not tenant-scoped, same category as
-- subscription_plans): the seller-selectable premium storefront templates.
-- Moved here (out of a static Python list) so adding/editing one is a data
-- change, not a code deploy -- see app/services/storefront_templates.py.
CREATE TABLE storefront_templates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    template_key VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    tagline VARCHAR(255) NOT NULL,
    swatch_json JSON NOT NULL,
    pages_json JSON NOT NULL,
    display_order INT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ================================================================================
-- 7. PERFORMANCE COMPOSITE INDEXES
-- ================================================================================
CREATE INDEX idx_products_tenant_active ON products(tenant_id, is_active);
CREATE INDEX idx_products_marketplace ON products(show_in_marketplace, is_active);
CREATE INDEX idx_orders_master ON orders(master_order_id);
CREATE INDEX idx_memberships_user ON user_store_memberships(user_id);
CREATE INDEX idx_variants_tenant_product ON product_variants(tenant_id, product_id);
CREATE INDEX idx_orders_tenant_user ON orders(tenant_id, user_id);
CREATE INDEX idx_orders_tenant_status ON orders(tenant_id, status);
CREATE INDEX idx_audit_tenant_action ON audit_logs(tenant_id, action);