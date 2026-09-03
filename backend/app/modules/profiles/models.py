import uuid
from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import Index
from sqlmodel import Field, SQLModel


class Position(str, Enum):
    GOLEIRO = "GOLEIRO"
    ZAGUEIRO = "ZAGUEIRO"
    LATERAL = "LATERAL"
    VOLANTE = "VOLANTE"
    MEIA = "MEIA"
    ATACANTE = "ATACANTE"


class DominantFoot(str, Enum):
    DESTRO = "DESTRO"
    CANHOTO = "CANHOTO"
    AMBIDESTRO = "AMBIDESTRO"


class AthleteStatus(str, Enum):
    DISPONIVEL = "DISPONIVEL"
    CONTRATADO = "CONTRATADO"
    NAO_DISPONIVEL = "NAO_DISPONIVEL"


class AthleteProfile(SQLModel, table=True):
    """Perfil 1:1 do usuario com papel ATHLETE."""

    __tablename__ = "athlete_profiles"

    # Indice composto para a busca de olheiros, que filtra posicao e estado juntos. Fica
    # aqui (e nao so na migracao) para o `alembic check` nao acusar drift.
    __table_args__ = (
        Index("ix_athlete_profiles_position_state", "position", "state"),
    )

    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    # O tipo nativo NAO pode se chamar `position`: POSITION e palavra-chave do Postgres em
    # posicao de nome de tipo, entao `CREATE TABLE ... (position position)` e erro de
    # sintaxe (assim como `DROP TYPE position`). Nomear `athleteposition` evita depender de
    # aspas em todo lugar que referenciar o tipo. O nome da classe Python segue `Position`.
    position: Optional[Position] = Field(
        default=None,
        index=True,
        sa_type=sa.Enum(Position, name="athleteposition"),
    )
    birth_date: Optional[date] = Field(default=None, index=True)
    height_cm: Optional[int] = None
    dominant_foot: Optional[DominantFoot] = None
    state: Optional[str] = Field(default=None, max_length=2, index=True)
    city: Optional[str] = None
    current_club: Optional[str] = None
    bio: Optional[str] = None
    avatar_path: Optional[str] = None
    status: AthleteStatus = Field(default=AthleteStatus.DISPONIVEL)
    # Idade nunca e coluna: e derivada de `birth_date` na leitura.
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # `onupdate` do SQLAlchemy roda no cliente a cada UPDATE emitido pela ORM, entao nao
    # precisa de migracao nem trigger no banco -- mas so dispara quando o UPDATE passa pela
    # Session (nao em um `UPDATE` via SQL cru).
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"onupdate": lambda: datetime.now(timezone.utc)},
    )
