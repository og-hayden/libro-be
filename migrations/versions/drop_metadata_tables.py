"""Drop themes, characters, locations and related tables

Revision ID: drop_metadata_tables
Revises: c4397bbc5408
Create Date: 2025-01-11 07:05:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'drop_metadata_tables'
down_revision = '39713bb8ae5c'
branch_labels = None
depends_on = None

def upgrade():
    # Drop join tables first (due to foreign key constraints)
    op.drop_table('chapter_locations')
    op.drop_table('chapter_characters')
    op.drop_table('chapter_themes')
    op.drop_table('book_themes')
    
    # Drop main metadata tables
    op.drop_table('locations')
    op.drop_table('characters')
    op.drop_table('themes')

def downgrade():
    # Recreate themes table
    op.create_table('themes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('normalized_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_theme_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['parent_theme_id'], ['themes.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('normalized_name')
    )
    op.create_index(op.f('ix_themes_normalized_name'), 'themes', ['normalized_name'], unique=False)

    # Recreate characters table
    op.create_table('characters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('normalized_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('normalized_name')
    )
    op.create_index(op.f('ix_characters_normalized_name'), 'characters', ['normalized_name'], unique=False)

    # Recreate locations table
    op.create_table('locations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('normalized_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('normalized_name')
    )
    op.create_index(op.f('ix_locations_normalized_name'), 'locations', ['normalized_name'], unique=False)

    # Recreate join tables
    op.create_table('book_themes',
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('theme_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ),
        sa.ForeignKeyConstraint(['theme_id'], ['themes.id'], ),
        sa.PrimaryKeyConstraint('book_id', 'theme_id')
    )

    op.create_table('chapter_themes',
        sa.Column('chapter_id', sa.Integer(), nullable=False),
        sa.Column('theme_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id'], ),
        sa.ForeignKeyConstraint(['theme_id'], ['themes.id'], ),
        sa.PrimaryKeyConstraint('chapter_id', 'theme_id')
    )

    op.create_table('chapter_characters',
        sa.Column('chapter_id', sa.Integer(), nullable=False),
        sa.Column('character_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id'], ),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ),
        sa.PrimaryKeyConstraint('chapter_id', 'character_id')
    )

    op.create_table('chapter_locations',
        sa.Column('chapter_id', sa.Integer(), nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id'], ),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ),
        sa.PrimaryKeyConstraint('chapter_id', 'location_id')
    )
