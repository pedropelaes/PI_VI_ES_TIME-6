"""
Peneiras e inscrições: /api/v1/opportunities.
Spec: docs/superpowers/specs/2026-11-11-oportunidades-peneiras-design.md
"""
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.security import create_access_token, hash_password
from app.modules.identity.models import User, UserRole
from app.modules.opportunities.models import (
    Opportunity,
    OpportunityApplication,
    OpportunityMode,
)
from app.modules.profiles.models import AthleteProfile, Position

AGORA = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


def _usuario(session: Session, role: UserRole, first="Ana", last="Souza") -> User:
    user = User(
        email=f"{uuid.uuid4().hex[:10]}@teste.com",
        password_hash=hash_password("senha12345"),
        first_name=first,
        last_name=last,
        role=role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _atleta(
    session: Session,
    position: Position | None = Position.ATACANTE,
    birth_date: date | None = date(2008, 5, 1),  # 18 anos em AGORA
    first="Jeh",
) -> User:
    user = _usuario(session, UserRole.ATHLETE, first=first, last="Rodrigues")
    session.add(
        AthleteProfile(
            user_id=user.id, position=position, birth_date=birth_date, state="SP", city="Campinas"
        )
    )
    session.commit()
    return user


def test_apagar_peneira_apaga_inscricoes_em_cascata(session):
    clube = _usuario(session, UserRole.CLUB)
    atleta = _atleta(session)
    opp = Opportunity(
        organizer_id=clube.id,
        title="Peneira",
        description="Avaliação",
        mode=OpportunityMode.ONLINE,
        meeting_url="https://meet.example.com/x",
        event_at=AGORA + timedelta(days=10),
        registration_deadline=AGORA + timedelta(days=5),
    )
    session.add(opp)
    session.commit()
    session.add(OpportunityApplication(opportunity_id=opp.id, athlete_id=atleta.id))
    session.commit()

    session.execute(sa.delete(Opportunity).where(Opportunity.id == opp.id))
    session.commit()

    assert session.exec(select(OpportunityApplication)).all() == []


def test_inscricao_duplicada_viola_a_pk(session):
    clube = _usuario(session, UserRole.CLUB)
    atleta = _atleta(session)
    opp = Opportunity(
        organizer_id=clube.id,
        title="Peneira",
        description="Avaliação",
        mode=OpportunityMode.ONLINE,
        meeting_url="https://meet.example.com/x",
        event_at=AGORA + timedelta(days=10),
        registration_deadline=AGORA + timedelta(days=5),
    )
    session.add(opp)
    session.commit()
    session.add(OpportunityApplication(opportunity_id=opp.id, athlete_id=atleta.id))
    session.commit()

    session.add(OpportunityApplication(opportunity_id=opp.id, athlete_id=atleta.id))
    with pytest.raises(IntegrityError):
        session.commit()
