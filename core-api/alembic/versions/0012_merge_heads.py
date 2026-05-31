"""merge all branch heads

Revision ID: 0012
Revises: 0003, 0011, a8faead918b5
Create Date: 2026-05-05

"""
from alembic import op

revision = '0012'
down_revision = ('0003', '0011', 'a8faead918b5')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
