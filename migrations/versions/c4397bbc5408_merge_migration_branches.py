"""Merge migration branches

Revision ID: c4397bbc5408
Revises: 3d5d4db09863, remove_auth_tables, remove_user_notes
Create Date: 2025-09-06 21:25:23.361992

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4397bbc5408'
down_revision = ('3d5d4db09863', 'remove_auth_tables', 'remove_user_notes')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
