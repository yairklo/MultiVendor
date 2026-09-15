"""Expand digital_file_url and shipping_label_url column lengths to 2048.

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-15
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "products",
        "digital_file_url",
        existing_type=sa.String(512),
        type_=sa.String(2048),
        existing_nullable=True,
    )
    op.alter_column(
        "orders",
        "shipping_label_url",
        existing_type=sa.String(512),
        type_=sa.String(2048),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "orders",
        "shipping_label_url",
        existing_type=sa.String(2048),
        type_=sa.String(512),
        existing_nullable=True,
    )
    op.alter_column(
        "products",
        "digital_file_url",
        existing_type=sa.String(2048),
        type_=sa.String(512),
        existing_nullable=True,
    )
