"""Consultas de peneiras e inscrições."""
import uuid
from typing import Iterable, Optional

import sqlalchemy as sa
from sqlmodel import Session, func, select

from app.modules.identity.models import User, UserRole
from app.modules.opportunities.models import (
    ApplicationStatus,
    Opportunity,
    OpportunityApplication,
)
from app.modules.profiles.models import AthleteProfile, ClubProfile, ScoutProfile

# Inscrições que ocupam vaga. Recusada libera.
ATIVAS = (ApplicationStatus.PENDENTE, ApplicationStatus.APROVADA)


def ocupadas_de(contagem: dict) -> int:
    return sum(contagem.get(status, 0) for status in ATIVAS)


class OpportunityRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, opp_id: uuid.UUID, lock: bool = False) -> Optional[Opportunity]:
        stmt = select(Opportunity).where(Opportunity.id == opp_id)
        if lock:
            # Serializa inscrições/edições concorrentes na mesma peneira (última vaga).
            stmt = stmt.with_for_update()
        return self.session.exec(stmt).first()

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
