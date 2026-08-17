"""Baseline schema: global users + memberships + marketplace + order splitting

This is the first Alembic revision in the project (no prior migration chain
existed -- schema changes used to be applied by hand-running db/schema.sql
and one-off ALTER scripts). Per the global-identity migration, existing dev
data is not preserved, so this revision creates the full target schema from
an empty database rather than ALTER-ing the old per-tenant `users` shape in
place. db/schema.sql mirrors this exact DDL and is the source of truth for
fresh container bootstraps; keep the two in sync by hand for now.

Revision ID: 0001
Revises:
Create Date: 2026-08-17

"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

# Statements run in FK-dependency order. Kept as raw SQL (not op.create_table)
# so this migration is a byte-for-byte mirror of db/schema.sql's CREATE TABLE
# bodies -- one source of DDL truth, copy-pasted into two places that are
# meant to be read together, not two independently-maintained schemas.
_UPGRADE_STATEMENTS = [
    """
    CREATE TABLE subscription_plans (
        id INT AUTO_INCREMENT PRIMARY KEY,
        code VARCHAR(50) NOT NULL UNIQUE,
        name VARCHAR(100) NOT NULL,
        price_monthly DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
        max_products INT NOT NULL DEFAULT 50,
        max_storage_mb INT NOT NULL DEFAULT 500,
        features_json JSON NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE tenants (
        id INT AUTO_INCREMENT PRIMARY KEY,
        slug VARCHAR(100) NOT NULL UNIQUE,
        name VARCHAR(255) NOT NULL,
        plan_id INT NOT NULL,
        status ENUM('active', 'suspended', 'cancelled') NOT NULL DEFAULT 'active',
        custom_domain VARCHAR(255) UNIQUE NULL,
        show_all_products_in_marketplace BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (plan_id) REFERENCES subscription_plans(id)
    ) ENGINE=InnoDB
    """,
    """
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
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE tenant_billing_logs (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        tenant_id INT NOT NULL,
        amount DECIMAL(10, 2) NOT NULL,
        currency VARCHAR(3) DEFAULT 'USD',
        status ENUM('paid', 'failed', 'pending') NOT NULL,
        invoice_url TEXT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE users (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        email VARCHAR(255) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        full_name VARCHAR(255) NOT NULL,
        role ENUM('super_admin', 'user') NOT NULL DEFAULT 'user',
        is_active BOOLEAN DEFAULT TRUE,
        last_login_at TIMESTAMP NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB
    """,
    """
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
    ) ENGINE=InnoDB
    """,
    """
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
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE categories (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        tenant_id INT NOT NULL,
        parent_id BIGINT NULL,
        name JSON NOT NULL,
        slug VARCHAR(100) NOT NULL,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
        FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL,
        CONSTRAINT uq_categories_tenant_slug UNIQUE (tenant_id, slug)
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE products (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        tenant_id INT NOT NULL,
        category_id BIGINT NULL,
        name JSON NOT NULL,
        slug VARCHAR(255) NOT NULL,
        description JSON NULL,
        base_price DECIMAL(10, 2) NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        show_in_marketplace BOOLEAN NOT NULL DEFAULT FALSE,
        product_type ENUM('physical', 'digital', 'service') DEFAULT 'physical',
        digital_file_url VARCHAR(512) NULL,
        download_limit INT NULL,
        is_bundle BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
        CONSTRAINT uq_products_tenant_slug UNIQUE (tenant_id, slug)
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE product_variants (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        tenant_id INT NOT NULL,
        product_id BIGINT NOT NULL,
        sku VARCHAR(100) NOT NULL,
        attributes_json JSON NULL,
        price_override DECIMAL(10, 2) NULL,
        stock_quantity INT NOT NULL DEFAULT 0,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
        CONSTRAINT uq_variants_tenant_sku UNIQUE (tenant_id, sku)
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE product_images (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        tenant_id INT NOT NULL,
        product_id BIGINT NOT NULL,
        image_url TEXT NOT NULL,
        is_primary BOOLEAN DEFAULT FALSE,
        sort_order INT DEFAULT 0,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """,
    """
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
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE product_bundle_items (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        bundle_product_id BIGINT NOT NULL,
        component_variant_id BIGINT NOT NULL,
        quantity INT NOT NULL DEFAULT 1,
        FOREIGN KEY (bundle_product_id) REFERENCES products(id) ON DELETE CASCADE,
        FOREIGN KEY (component_variant_id) REFERENCES product_variants(id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """,
    """
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
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE shipping_methods (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        tenant_id INT NOT NULL,
        name VARCHAR(100) NOT NULL,
        price DECIMAL(10, 2) NOT NULL,
        free_shipping_threshold DECIMAL(10, 2) NULL,
        is_active BOOLEAN DEFAULT TRUE,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE carts (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id INT NOT NULL,
        user_id BIGINT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE cart_items (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        tenant_id INT NOT NULL,
        cart_id VARCHAR(36) NOT NULL,
        variant_id BIGINT NOT NULL,
        quantity INT NOT NULL DEFAULT 1,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
        FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
        FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE marketplace_cart_items (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        cart_id VARCHAR(36) NOT NULL,
        tenant_id INT NOT NULL,
        variant_id BIGINT NOT NULL,
        quantity INT NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
        FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """,
    "CREATE INDEX idx_marketplace_cart_items_cart ON marketplace_cart_items(cart_id)",
    """
    CREATE TABLE master_orders (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        user_id BIGINT NOT NULL,
        master_order_number VARCHAR(50) NOT NULL UNIQUE,
        total_amount DECIMAL(10, 2) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE orders (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        tenant_id INT NOT NULL,
        user_id BIGINT NOT NULL,
        coupon_id BIGINT NULL,
        master_order_id BIGINT NULL,
        order_number VARCHAR(50) NOT NULL,
        subtotal DECIMAL(10, 2) NOT NULL,
        discount_amt DECIMAL(10, 2) DEFAULT 0.00,
        shipping_method_id BIGINT NULL,
        shipping_fee DECIMAL(10, 2) DEFAULT 0.00,
        total_amount DECIMAL(10, 2) NOT NULL,
        platform_commission DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
        vendor_net_payout DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
        status ENUM('pending', 'pending_payment', 'processing', 'completed', 'cancelled', 'expired') DEFAULT 'pending',
        order_type ENUM('physical', 'digital') DEFAULT 'physical',
        shipping_json JSON NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (coupon_id) REFERENCES coupons(id) ON DELETE SET NULL,
        FOREIGN KEY (master_order_id) REFERENCES master_orders(id) ON DELETE SET NULL,
        FOREIGN KEY (shipping_method_id) REFERENCES shipping_methods(id) ON DELETE SET NULL,
        CONSTRAINT uq_orders_tenant_number UNIQUE (tenant_id, order_number)
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE order_items (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        tenant_id INT NOT NULL,
        order_id BIGINT NOT NULL,
        variant_id BIGINT NULL,
        product_name VARCHAR(255) NOT NULL,
        sku VARCHAR(100) NOT NULL,
        unit_price DECIMAL(10, 2) NOT NULL,
        quantity INT NOT NULL,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY (variant_id) REFERENCES product_variants(id) ON DELETE SET NULL
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE store_pages (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        tenant_id INT NOT NULL,
        page_key VARCHAR(100) NOT NULL,
        page_type ENUM('static_page', 'template') NOT NULL DEFAULT 'static_page',
        title VARCHAR(255) NOT NULL,
        sections JSON NOT NULL,
        background_color VARCHAR(20) NULL,
        text_color VARCHAR(20) NULL,
        published_sections JSON NULL,
        published_title VARCHAR(255) NULL,
        published_background_color VARCHAR(20) NULL,
        published_text_color VARCHAR(20) NULL,
        published_at TIMESTAMP NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
        CONSTRAINT uq_store_pages_tenant_key_type UNIQUE (tenant_id, page_key, page_type)
    ) ENGINE=InnoDB
    """,
    """
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
    ) ENGINE=InnoDB
    """,
    """
    CREATE TABLE ai_conversations (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        tenant_id INT NOT NULL,
        page_key VARCHAR(100) NULL,
        page_type ENUM('static_page', 'template') NULL,
        gemini_history JSON NULL,
        messages JSON NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        page_key_uq VARCHAR(100) AS (COALESCE(page_key, '')) STORED,
        page_type_uq VARCHAR(20) AS (COALESCE(page_type, '')) STORED,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
        CONSTRAINT uq_ai_conversations_tenant_key_type UNIQUE (tenant_id, page_key_uq, page_type_uq)
    ) ENGINE=InnoDB
    """,
    "CREATE INDEX idx_store_page_versions_page ON store_page_versions(tenant_id, store_page_id, created_at)",
    """
    CREATE TABLE ai_pending_actions (
        id CHAR(36) PRIMARY KEY,
        tenant_id INT NOT NULL,
        tool_name VARCHAR(100) NOT NULL,
        tool_args JSON NOT NULL,
        summary VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """,
    "CREATE INDEX idx_products_tenant_active ON products(tenant_id, is_active)",
    "CREATE INDEX idx_products_marketplace ON products(show_in_marketplace, is_active)",
    "CREATE INDEX idx_variants_tenant_product ON product_variants(tenant_id, product_id)",
    "CREATE INDEX idx_orders_tenant_user ON orders(tenant_id, user_id)",
    "CREATE INDEX idx_orders_tenant_status ON orders(tenant_id, status)",
    "CREATE INDEX idx_orders_master ON orders(master_order_id)",
    "CREATE INDEX idx_memberships_user ON user_store_memberships(user_id)",
    "CREATE INDEX idx_audit_tenant_action ON audit_logs(tenant_id, action)",
]

# Reverse dependency order so FKs never block a DROP.
_DOWNGRADE_TABLES = [
    "ai_pending_actions",
    "ai_conversations",
    "store_page_versions",
    "store_pages",
    "order_items",
    "orders",
    "master_orders",
    "marketplace_cart_items",
    "cart_items",
    "carts",
    "shipping_methods",
    "coupons",
    "product_bundle_items",
    "product_reviews",
    "product_images",
    "product_variants",
    "products",
    "categories",
    "audit_logs",
    "user_store_memberships",
    "users",
    "tenant_billing_logs",
    "tenant_settings",
    "tenants",
    "subscription_plans",
]


def upgrade() -> None:
    for statement in _UPGRADE_STATEMENTS:
        op.execute(sa.text(statement))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("SET FOREIGN_KEY_CHECKS=0"))
    for table in _DOWNGRADE_TABLES:
        conn.execute(sa.text(f"DROP TABLE IF EXISTS {table}"))
    conn.execute(sa.text("SET FOREIGN_KEY_CHECKS=1"))
