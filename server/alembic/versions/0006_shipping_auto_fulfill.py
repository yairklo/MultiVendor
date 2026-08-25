"""Add auto_fulfill to tenant_shipping_configs

Opt-in per-tenant flag: when true, shipping_service.maybe_auto_fulfill_order
dispatches a shipment automatically the moment an order is marked
'processing' (paid), instead of waiting for the vendor to click "Fulfill"
manually. Off by default.

db/schema.sql mirrors this ALTER (source of truth for fresh container
bootstraps, same convention as 0001-0005).

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-25

"""
from alembic import op
import sqlalchemy as sa

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text(
        "ALTER TABLE tenant_shipping_configs ADD COLUMN auto_fulfill BOOLEAN NOT NULL DEFAULT FALSE AFTER is_default"
    ))


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE tenant_shipping_configs DROP COLUMN auto_fulfill"))
