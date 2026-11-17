import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def _agora() -> datetime:
    return datetime.now(timezone.utc)


_TZ = sa.DateTime(timezone=True)


class OpportunityMode(str, Enum):
    PRESENCIAL = "PRESENCIAL"
    ONLINE = "ONLINE"


class ApplicationStatus(str, Enum):
    PENDENTE = "PENDENTE"
    APROVADA = "APROVADA"
    RECUSADA = "RECUSADA"


class Opportunity(SQLModel, table=True):
    """Peneira publicada por um CLUB ou SCOUT. "Aberta" é derivado (spec D5), não coluna."""

    __tablename__ = "opportunities"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    organizer_id: uuid.UUID = Field(foreign_key="users.id", index=True, ondelete="CASCADE")
    title: str = Field(max_length=120)
    description: str
    mode: OpportunityMode = Field(sa_type=sa.Enum(OpportunityMode, name="opportunitymode"))
    state: Optional[str] = Field(default=None, max_length=2, index=True)
    city: Optional[str] = None
    address: Optional[str] = None
    meeting_url: Optional[str] = None
    event_at: datetime = Field(sa_type=_TZ, index=True)
    registration_deadline: datetime = Field(sa_type=_TZ, index=True)
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    # JSONB (e não JSON como em club_profiles) porque a lista filtra por `@>`.
    # Vazio = qualquer posição.
    positions: List[str] = Field(
        default_factory=list, sa_column=sa.Column(JSONB, nullable=False, server_default="[]")
    )
    max_applications: Optional[int] = None
    cancelled_at: Optional[datetime] = Field(default=None, sa_type=_TZ)
    created_at: datetime = Field(default_factory=_agora, sa_type=_TZ)
    updated_at: datetime = Field(
        default_factory=_agora, sa_type=_TZ, sa_column_kwargs={"onupdate": _agora}
    )


class OpportunityApplication(SQLModel, table=True):
    """Inscrição de um atleta numa peneira. A PK composta impede inscrição duplicada."""

    __tablename__ = "opportunity_applications"

    opportunity_id: uuid.UUID = Field(
        foreign_key="opportunities.id", primary_key=True, ondelete="CASCADE"
    )
    athlete_id: uuid.UUID = Field(
        foreign_key="users.id", primary_key=True, index=True, ondelete="CASCADE"
    )
    status: ApplicationStatus = Field(
        default=ApplicationStatus.PENDENTE,
        sa_type=sa.Enum(ApplicationStatus, name="applicationstatus"),
    )
    created_at: datetime = Field(default_factory=_agora, sa_type=_TZ)
    updated_at: datetime = Field(
        default_factory=_agora, sa_type=_TZ, sa_column_kwargs={"onupdate": _agora}
    )
