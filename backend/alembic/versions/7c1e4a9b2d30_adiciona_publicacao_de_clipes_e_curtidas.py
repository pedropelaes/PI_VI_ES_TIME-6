"""adiciona publicacao de clipes (published_at) e curtidas (clip_likes)

Revision ID: 7c1e4a9b2d30
Revises: a1b2c3d4e5f6
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '7c1e4a9b2d30'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('clips', sa.Column('published_at', sa.DateTime(), nullable=True))
    op.create_index('ix_clips_status_published_at', 'clips', ['status', 'published_at'], unique=False)

    op.create_table('clip_likes',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('clip_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['clip_id'], ['clips.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'clip_id'),
    )
    op.create_index(op.f('ix_clip_likes_clip_id'), 'clip_likes', ['clip_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_clip_likes_clip_id'), table_name='clip_likes')
    op.drop_table('clip_likes')
    op.drop_index('ix_clips_status_published_at', table_name='clips')
    op.drop_column('clips', 'published_at')