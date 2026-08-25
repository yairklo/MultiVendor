"""stripe_connect

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-25 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0007'
down_revision = '0006'

def upgrade():
    op.add_column('tenants', sa.Column('stripe_account_id', sa.String(length=255), nullable=True))

def downgrade():
    op.drop_column('tenants', 'stripe_account_id')

