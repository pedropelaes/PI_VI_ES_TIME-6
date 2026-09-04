import uuid
from datetime import date, datetime, timezone
from enum import Enum
from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy import Index
from sqlmodel import Field, SQLModel


def _agora() -> datetime:
    return datetime.now(timezone.utc)


# `onupdate` do SQLAlchemy roda no cliente a cada UPDATE emitido pela ORM, entao nao
# precisa de migracao nem trigger -- mas so dispara quando o UPDATE passa pela Session
# (nao em um `UPDATE` via SQL cru).
_TIMESTAMPS = {"onupdate": _agora}


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
    # Texto livre multilinha (decisao E1): o atleta escreve os clubes por onde passou
    # do jeito que quiser. Quando virar tabela propria, migrar este texto e trabalho
    # proprio -- ver secao 7 da spec.
    club_history: Optional[str] = None
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


class ClubCategory(str, Enum):
    """Categorias de base que um clube declara atender."""

    SUB_15 = "SUB_15"
    SUB_17 = "SUB_17"
    SUB_20 = "SUB_20"
    PROFISSIONAL = "PROFISSIONAL"


class ScoutProfile(SQLModel, table=True):
    """Perfil 1:1 do usuario com papel SCOUT."""

    __tablename__ = "scout_profiles"
    __table_args__ = (Index("ix_scout_profiles_state_city", "state", "city"),)

    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    organization: Optional[str] = Field(default=None, index=True)
    credential: Optional[str] = None
    state: Optional[str] = Field(default=None, max_length=2, index=True)
    city: Optional[str] = None
    bio: Optional[str] = None
    avatar_path: Optional[str] = None
    created_at: datetime = Field(default_factory=_agora)
    updated_at: datetime = Field(default_factory=_agora, sa_column_kwargs=_TIMESTAMPS)


class ClubProfile(SQLModel, table=True):
    """Perfil 1:1 do usuario com papel CLUB."""

    __tablename__ = "club_profiles"
    __table_args__ = (Index("ix_club_profiles_state_city", "state", "city"),)

    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    legal_name: Optional[str] = None
    # Guardado como texto livre nesta fatia: validar digito verificador e regra de
    # negocio que merece decisao propria (secao 8 da spec).
    cnpj: Optional[str] = Field(default=None, max_length=14, index=True)
    categories: List[str] = Field(
        default_factory=list, sa_column=sa.Column(sa.JSON, nullable=False, server_default="[]")
    )
    state: Optional[str] = Field(default=None, max_length=2, index=True)
    city: Optional[str] = None
    bio: Optional[str] = None
    avatar_path: Optional[str] = None
    created_at: datetime = Field(default_factory=_agora)
    updated_at: datetime = Field(default_factory=_agora, sa_column_kwargs=_TIMESTAMPS)
