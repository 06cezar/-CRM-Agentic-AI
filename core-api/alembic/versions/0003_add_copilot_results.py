"""add copilot_results table

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'copilot_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lead_id', sa.Integer(), sa.ForeignKey('leads.id'), nullable=False),
        sa.Column('winning_argument', sa.Text(), nullable=True),
        sa.Column('draft_message', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('model_used', sa.String(100), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('lead_snapshot', JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lead_id', name='uq_copilot_results_lead_id'),
    )
    op.create_index('ix_copilot_results_id', 'copilot_results', ['id'])
    op.create_index('ix_copilot_results_lead_id', 'copilot_results', ['lead_id'])


def downgrade():
    op.drop_index('ix_copilot_results_lead_id', table_name='copilot_results')
    op.drop_index('ix_copilot_results_id', table_name='copilot_results')
    op.drop_table('copilot_results')
