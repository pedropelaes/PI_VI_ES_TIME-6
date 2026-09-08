"""junta retencao e perfis

Revision ID: ec4e15ee81af
Revises: b1a2c3d4e5f6, ece9ca6c34d4
Create Date: 2026-09-03 18:27:29.171347

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'ec4e15ee81af'
down_revision: Union[str, Sequence[str], None] = ('b1a2c3d4e5f6', 'ece9ca6c34d4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
