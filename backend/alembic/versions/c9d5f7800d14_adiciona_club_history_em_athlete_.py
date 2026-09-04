"""adiciona club_history em athlete_profiles

Revision ID: c9d5f7800d14
Revises: ee15ae38b49f
Create Date: 2026-09-04 13:07:18.149019

Histórico de clubes como texto livre multilinha (decisão E1 da spec de edição de
perfil). Sem backfill: os perfis que já existem ficam com NULL.

`AutoString` (o mapeamento de `Optional[str]` no SQLModel) vira VARCHAR sem limite no
Postgres, que é o mesmo armazenamento de TEXT -- é o tipo que `bio` e `current_club` já
usam nesta tabela. Usar `sa.Text()` aqui só produziria drift no `alembic check` contra o
model.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'c9d5f7800d14'
down_revision: Union[str, Sequence[str], None] = 'ee15ae38b49f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "athlete_profiles",
        sa.Column("club_history", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("athlete_profiles", "club_history")
