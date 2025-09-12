"""Remove user_notes table

Revision ID: remove_user_notes
Revises: 
Create Date: 2025-01-05 21:08:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_user_notes'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Drop the user_notes table
    op.drop_table('user_notes')


def downgrade():
    # Recreate the user_notes table if needed
    op.create_table('user_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('verse_id', sa.Integer(), nullable=False),
        sa.Column('note_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['verse_id'], ['verses.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
