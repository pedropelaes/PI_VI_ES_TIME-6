"""feed: timestamps com fuso e FK de usuario com ondelete CASCADE

Revision ID: e5f1a2b3c4d6
Revises: 7c1e4a9b2d30
Create Date: 2026-11-09 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5f1a2b3c4d6'
down_revision: Union[str, None] = '7c1e4a9b2d30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Os valores antigos foram gravados em UTC sem fuso: AT TIME ZONE 'UTC' preserva o instante.
    op.alter_column(
        'clips', 'published_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        postgresql_using="published_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'clip_likes', 'created_at',
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
    op.drop_constraint('clip_likes_user_id_fkey', 'clip_likes', type_='foreignkey')
    op.create_foreign_key(
        'clip_likes_user_id_fkey', 'clip_likes', 'users', ['user_id'], ['id'], ondelete='CASCADE'
    )


def downgrade() -> None:
    op.drop_constraint('clip_likes_user_id_fkey', 'clip_likes', type_='foreignkey')
    op.create_foreign_key('clip_likes_user_id_fkey', 'clip_likes', 'users', ['user_id'], ['id'])
    op.alter_column(
        'clip_likes', 'created_at',
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        'clips', 'published_at',
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        postgresql_using="published_at AT TIME ZONE 'UTC'",
    )