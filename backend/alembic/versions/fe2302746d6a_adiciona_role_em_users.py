"""adiciona role em users

Revision ID: fe2302746d6a
Revises: dc5867a2d8e8
Create Date: 2026-09-03 00:41:03.117236

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fe2302746d6a'
down_revision: Union[str, Sequence[str], None] = 'dc5867a2d8e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role = sa.Enum("ATHLETE", "SCOUT", "CLUB", name="userrole")


def upgrade() -> None:
    """Upgrade schema."""
    user_role.create(op.get_bind(), checkfirst=True)
    # Nullable primeiro para nao quebrar as linhas existentes.
    #
    # Os tres passos rodam numa transacao so, entao o ACCESS EXCLUSIVE do add_column fica
    # retido durante o UPDATE e o scan do SET NOT NULL. Irrelevante no tamanho atual da
    # tabela; se `users` crescer muito, quebre isto em migracoes separadas com o UPDATE
    # em lotes.
    op.add_column("users", sa.Column("role", user_role, nullable=True))
    op.execute("UPDATE users SET role = 'ATHLETE' WHERE role IS NULL")
    op.alter_column("users", "role", nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "role")
    user_role.drop(op.get_bind(), checkfirst=True)
