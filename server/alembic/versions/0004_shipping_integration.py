"""Shipping integration: tenant courier credentials + order fulfillment fields

Adds tenant_shipping_configs (per-tenant, per-courier encrypted credentials --
see app/core/crypto.py and app/models/shipping_config.py) and the fulfillment
columns on orders (tracking_number, shipping_label_url, shipping_provider,
shipped_at) populated by app/services/shipping_service.py via the
israel-shipping-sdk package (packages/israel-shipping-sdk). Also widens
orders.status to add 'shipped', sitting between 'processing' and 'completed'.

db/schema.sql mirrors these changes (source of truth for fresh container
bootstraps, same convention as 0001/0002/0003).

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-24

"""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None

_CREATE_TABLE = """
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT uq_tenant_shipping_provider UNIQUE (tenant_id, provider)
) ENGINE=InnoDB
"""

_UPGRADE_STATEMENTS = [
    "ALTER TABLE orders MODIFY COLUMN status ENUM('pending', 'pending_payment', 'processing', 'shipped', 'completed', 'cancelled', 'expired') DEFAULT 'pending'",
    "ALTER TABLE orders ADD COLUMN tracking_number VARCHAR(255) NULL AFTER payment_intent_id",
    "ALTER TABLE orders ADD COLUMN shipping_label_url VARCHAR(512) NULL AFTER tracking_number",
    "ALTER TABLE orders ADD COLUMN shipping_provider ENUM('hfd', 'lionwheel') NULL AFTER shipping_label_url",
    "ALTER TABLE orders ADD COLUMN shipped_at TIMESTAMP NULL AFTER shipping_provider",
]


def upgrade() -> None:
    op.execute(sa.text(_CREATE_TABLE))
    for statement in _UPGRADE_STATEMENTS:
        op.execute(sa.text(statement))


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE orders DROP COLUMN shipped_at"))
    op.execute(sa.text("ALTER TABLE orders DROP COLUMN shipping_provider"))
    op.execute(sa.text("ALTER TABLE orders DROP COLUMN shipping_label_url"))
    op.execute(sa.text("ALTER TABLE orders DROP COLUMN tracking_number"))
    op.execute(sa.text(
        "ALTER TABLE orders MODIFY COLUMN status "
        "ENUM('pending', 'pending_payment', 'processing', 'completed', 'cancelled', 'expired') DEFAULT 'pending'"
    ))
    op.execute(sa.text("DROP TABLE IF EXISTS tenant_shipping_configs"))
