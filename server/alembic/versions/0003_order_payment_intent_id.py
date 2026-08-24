"""Add payment_intent_id to orders and master_orders

Backing columns for the real Stripe integration (app/services/payments/):
lets the webhook look up which order/master_order a PaymentIntent belongs to
without trusting anything the client reports. NULL for mock-mode orders.

db/schema.sql mirrors these ALTERs (source of truth for fresh container
bootstraps, same convention as 0001/0002).

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-23

"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None

_UPGRADE_STATEMENTS = [
    "ALTER TABLE orders ADD COLUMN payment_intent_id VARCHAR(255) NULL UNIQUE AFTER shipping_json",
    "ALTER TABLE master_orders ADD COLUMN payment_intent_id VARCHAR(255) NULL UNIQUE AFTER total_amount",
]


def upgrade() -> None:
    for statement in _UPGRADE_STATEMENTS:
        op.execute(sa.text(statement))


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE orders DROP COLUMN payment_intent_id"))
    op.execute(sa.text("ALTER TABLE master_orders DROP COLUMN payment_intent_id"))
