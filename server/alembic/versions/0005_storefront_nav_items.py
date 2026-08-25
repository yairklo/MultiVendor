"""Add tenant_settings.nav_items for seller-editable storefront navigation.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-24

"""
from alembic import op
import sqlalchemy as sa

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tenant_settings', sa.Column('nav_items', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('tenant_settings', 'nav_items')
