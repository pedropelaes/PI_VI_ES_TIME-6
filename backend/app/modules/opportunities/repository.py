"""Consultas de peneiras e inscrições."""
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional

import sqlalchemy as sa
from sqlmodel import Session, func, select

from app.modules.feed.repository import _escapa_like
from app.modules.identity.models import User, UserRole
from app.modules.opportunities.models import (
    ApplicationStatus,
    Opportunity,
    OpportunityApplication,
    OpportunityMode,
)
from app.modules.profiles.models import AthleteProfile, ClubProfile, Position, ScoutProfile

# Inscrições que ocupam vaga. Recusada libera.
ATIVAS = (ApplicationStatus.PENDENTE, ApplicationStatus.APROVADA)


def ocupadas_de(contagem: dict) -> int:
    return sum(contagem.get(status, 0) for status in ATIVAS)


@dataclass(frozen=True)
class ListFilters:
    mode: Optional[OpportunityMode] = None
    state: Optional[str] = None
    position: Optional[Position] = None
    query: Optional[str] = None
    # "elegíveis para mim": idade/posição do atleta logado (None = não preenchido).
    only_eligible: bool = False
    athlete_age: Optional[int] = None
    athlete_position: Optional[Position] = None


def _ocupadas_sql():
    return (
        select(func.count())
        .select_from(OpportunityApplication)
        .where(OpportunityApplication.opportunity_id == Opportunity.id)
        .where(OpportunityApplication.status.in_(ATIVAS))
        .correlate(Opportunity)
        .scalar_subquery()
    )


def _sem_restricao_de_posicao():
    return func.jsonb_array_length(Opportunity.positions) == 0


def _aceita_posicao(position: Position):
    return sa.or_(_sem_restricao_de_posicao(), Opportunity.positions.contains([position.value]))


class OpportunityRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, opp_id: uuid.UUID, lock: bool = False) -> Optional[Opportunity]:
        stmt = select(Opportunity).where(Opportunity.id == opp_id)
        if lock:
            # Serializa inscrições/edições concorrentes na mesma peneira (última vaga).
            stmt = stmt.with_for_update()
        return self.session.exec(stmt).first()

    def list_open(
        self,
        filters: ListFilters,
        agora: datetime,
        limit: int,
        after: Optional[tuple[datetime, uuid.UUID]] = None,
    ) -> List[tuple[Opportunity, User, int]]:
        """Peneiras abertas (spec D5), evento mais próximo primeiro. Cursor em (event_at, id)."""
        ocupadas = _ocupadas_sql()
        stmt = (
            select(Opportunity, User, ocupadas.label("ocupadas"))
            .join(User, User.id == Opportunity.organizer_id)
            .where(Opportunity.cancelled_at.is_(None))
            .where(Opportunity.registration_deadline >= agora)
            .where(
                sa.or_(
                    Opportunity.max_applications.is_(None),
                    Opportunity.max_applications > ocupadas,
                )
            )
        )

        if filters.mode is not None:
            stmt = stmt.where(Opportunity.mode == filters.mode)
        if filters.state is not None:
            stmt = stmt.where(Opportunity.state == filters.state)
        if filters.position is not None:
            stmt = stmt.where(_aceita_posicao(filters.position))
        if filters.query:
            termo = f"%{_escapa_like(filters.query)}%"
            nome = func.concat(User.first_name, " ", User.last_name)
            stmt = stmt.where(
                sa.or_(
                    Opportunity.title.ilike(termo, escape="\\"),
                    nome.ilike(termo, escape="\\"),
                )
            )
        if filters.only_eligible:
            idade = filters.athlete_age
            if idade is None:
                stmt = stmt.where(Opportunity.min_age.is_(None), Opportunity.max_age.is_(None))
            else:
                stmt = stmt.where(
                    sa.or_(Opportunity.min_age.is_(None), Opportunity.min_age <= idade),
                    sa.or_(Opportunity.max_age.is_(None), Opportunity.max_age >= idade),
                )
            if filters.athlete_position is None:
                stmt = stmt.where(_sem_restricao_de_posicao())
            else:
                stmt = stmt.where(_aceita_posicao(filters.athlete_position))

        if after is not None:
            stmt = stmt.where(sa.tuple_(Opportunity.event_at, Opportunity.id) > sa.tuple_(*after))

        stmt = stmt.order_by(Opportunity.event_at, Opportunity.id).limit(limit)
        return list(self.session.exec(stmt).all())

    def delete(self, opp_id: uuid.UUID) -> None:
        # Inscrições vão junto pelo ondelete=CASCADE.
        self.session.execute(sa.delete(Opportunity).where(Opportunity.id == opp_id))

    def counts_by_status(
        self, opp_ids: Iterable[uuid.UUID]
    ) -> dict[uuid.UUID, dict[ApplicationStatus, int]]:
        ids = list(opp_ids)
        if not ids:
            return {}
        rows = self.session.exec(
            select(
                OpportunityApplication.opportunity_id,
                OpportunityApplication.status,
                func.count(),
            )
            .where(OpportunityApplication.opportunity_id.in_(ids))
            .group_by(OpportunityApplication.opportunity_id, OpportunityApplication.status)
        ).all()
        contagens: dict[uuid.UUID, dict[ApplicationStatus, int]] = {}
        for opp_id, status, total in rows:
            contagens.setdefault(opp_id, {})[status] = total
        return contagens

    def occupied(self, opp_id: uuid.UUID) -> int:
        return ocupadas_de(self.counts_by_status([opp_id]).get(opp_id, {}))

    def get_application(
        self, opp_id: uuid.UUID, athlete_id: uuid.UUID
    ) -> Optional[OpportunityApplication]:
        return self.session.get(OpportunityApplication, (opp_id, athlete_id))

    def athlete_profile(self, user_id: uuid.UUID) -> Optional[AthleteProfile]:
        return self.session.get(AthleteProfile, user_id)

    def organizer_avatar(self, user: User) -> Optional[str]:
        modelo = ClubProfile if user.role == UserRole.CLUB else ScoutProfile
        perfil = self.session.get(modelo, user.id)
        return perfil.avatar_path if perfil else None

    def list_by_athlete(
        self, athlete_id: uuid.UUID
    ) -> List[tuple[OpportunityApplication, Opportunity, User]]:
        stmt = (
            select(OpportunityApplication, Opportunity, User)
            .join(Opportunity, Opportunity.id == OpportunityApplication.opportunity_id)
            .join(User, User.id == Opportunity.organizer_id)
            .where(OpportunityApplication.athlete_id == athlete_id)
            .order_by(Opportunity.event_at.desc())
        )
        return list(self.session.exec(stmt).all())

    def list_by_organizer(self, organizer_id: uuid.UUID) -> List[Opportunity]:
        return list(
            self.session.exec(
                select(Opportunity)
                .where(Opportunity.organizer_id == organizer_id)
                .order_by(Opportunity.event_at.desc())
            ).all()
        )

    def list_applicants(
        self, opp_id: uuid.UUID, status: Optional[ApplicationStatus] = None
    ) -> List[tuple[OpportunityApplication, User, Optional[AthleteProfile]]]:
        stmt = (
            select(OpportunityApplication, User, AthleteProfile)
            .join(User, User.id == OpportunityApplication.athlete_id)
            .outerjoin(AthleteProfile, AthleteProfile.user_id == User.id)
            .where(OpportunityApplication.opportunity_id == opp_id)
        )
        if status is not None:
            stmt = stmt.where(OpportunityApplication.status == status)
        return list(self.session.exec(stmt.order_by(OpportunityApplication.created_at)).all())
