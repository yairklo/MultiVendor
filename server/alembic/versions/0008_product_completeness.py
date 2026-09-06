"""Add tenant_settings product-completeness enforcement flags.

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-06

db/schema.sql mirrors these ALTERs (source of truth for fresh container
bootstraps). Store managers opt in with require_product_completeness;
platform admins can hard-lock a store with force_product_completeness.
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenant_settings",
        sa.Column("require_product_completeness", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "tenant_settings",
        sa.Column("force_product_completeness", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("tenant_settings", "force_product_completeness")
    op.drop_column("tenant_settings", "require_product_completeness")
