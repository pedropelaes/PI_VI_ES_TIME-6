"""cria athlete_profiles

Revision ID: ece9ca6c34d4
Revises: fe2302746d6a
Create Date: 2026-09-03 17:04:41.374795

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'ece9ca6c34d4'
down_revision: Union[str, Sequence[str], None] = 'fe2302746d6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# O tipo se chama `athleteposition`, e nao `position`: POSITION e palavra-chave do
# Postgres em posicao de nome de tipo -- `CREATE TABLE ... (position position)` e
# `DROP TYPE position` sao erro de sintaxe sem aspas.
athlete_position = sa.Enum(
    "GOLEIRO", "ZAGUEIRO", "LATERAL", "VOLANTE", "MEIA", "ATACANTE",
    name="athleteposition",
)
dominant_foot = sa.Enum("DESTRO", "CANHOTO", "AMBIDESTRO", name="dominantfoot")
athlete_status = sa.Enum(
    "DISPONIVEL", "CONTRATADO", "NAO_DISPONIVEL", name="athletestatus"
)

# Backfill: todo usuario ATHLETE precisa de perfil (secao 5.1 da spec de origem).
#
# Constante de modulo, e nao um literal solto dentro do upgrade(), para o teste de
# idempotencia poder rodar exatamente este SQL duas vezes em vez de uma copia colada.
BACKFILL_ATLETAS = """
INSERT INTO athlete_profiles (user_id, status, created_at, updated_at)
SELECT id, 'DISPONIVEL', NOW(), NOW() FROM users WHERE role = 'ATHLETE'
ON CONFLICT (user_id) DO NOTHING
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "athlete_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("position", athlete_position, nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("height_cm", sa.Integer(), nullable=True),
        sa.Column("dominant_foot", dominant_foot, nullable=True),
        sa.Column("state", sqlmodel.sql.sqltypes.AutoString(length=2), nullable=True),
        sa.Column("city", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("current_club", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("bio", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("avatar_path", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("status", athlete_status, nullable=False, server_default="DISPONIVEL"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index("ix_athlete_profiles_position", "athlete_profiles", ["position"])
    op.create_index("ix_athlete_profiles_birth_date", "athlete_profiles", ["birth_date"])
    op.create_index("ix_athlete_profiles_state", "athlete_profiles", ["state"])
    op.create_index(
        "ix_athlete_profiles_position_state", "athlete_profiles", ["position", "state"]
    )

    op.execute(BACKFILL_ATLETAS)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_athlete_profiles_position_state", "athlete_profiles")
    op.drop_index("ix_athlete_profiles_state", "athlete_profiles")
    op.drop_index("ix_athlete_profiles_birth_date", "athlete_profiles")
    op.drop_index("ix_athlete_profiles_position", "athlete_profiles")
    op.drop_table("athlete_profiles")

    # Os tres tipos nascem junto com a tabela (create_table emite o CREATE TYPE), mas nao
    # morrem com ela: sem estes drops, o proximo upgrade estoura com "type already exists".
    bind = op.get_bind()
    athlete_status.drop(bind, checkfirst=True)
    dominant_foot.drop(bind, checkfirst=True)
    athlete_position.drop(bind, checkfirst=True)
