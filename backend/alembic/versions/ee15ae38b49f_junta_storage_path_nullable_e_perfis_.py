"""junta storage_path nullable e perfis scout clube

Revision ID: ee15ae38b49f
Revises: 9f57e595dc96, e2a3c4d5e6f7
Create Date: 2026-09-04 01:05:01.874808

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'ee15ae38b49f'
down_revision: Union[str, Sequence[str], None] = ('9f57e595dc96', 'e2a3c4d5e6f7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
