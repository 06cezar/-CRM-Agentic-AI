"""create linkedin_credentials table

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-05 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'linkedin_credentials',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('cookies_json', sa.Text(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
    )


def downgrade():
    op.drop_table('linkedin_credentials')
