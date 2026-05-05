"""add linkedin_url to leads

Revision ID: 0009
Revises: ec86383315c7
Create Date: 2026-05-05 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '0009'
down_revision = 'ec86383315c7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('leads', sa.Column('linkedin_url', sa.String(), nullable=True))
    op.create_index('ix_leads_linkedin_url_assigned_to', 'leads', ['linkedin_url', 'assigned_to'])


def downgrade():
    op.drop_index('ix_leads_linkedin_url_assigned_to', table_name='leads')
    op.drop_column('leads', 'linkedin_url')
