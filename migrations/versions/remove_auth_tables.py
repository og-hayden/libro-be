"""Remove authentication tables

Revision ID: remove_auth_tables
Revises: c4ffbc3ae93d
Create Date: 2025-01-06 20:59:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_auth_tables'
down_revision = 'c4ffbc3ae93d'
branch_labels = None
depends_on = None


def upgrade():
    # Drop user_analyses table first (has foreign key to users)
    op.drop_table('user_analyses')
    
    # Drop users table
    op.drop_table('users')


def downgrade():
    # Recreate users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=80), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('password_hash', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('preferred_perspectives', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    
    # Recreate user_analyses table
    op.create_table('user_analyses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('verse_range_start', sa.Integer(), nullable=False),
        sa.Column('verse_range_end', sa.Integer(), nullable=False),
        sa.Column('user_question', sa.Text(), nullable=False),
        sa.Column('ai_response', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['verse_range_start'], ['verses.id'], ),
        sa.ForeignKeyConstraint(['verse_range_end'], ['verses.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
