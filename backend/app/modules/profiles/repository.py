"""
Acesso a dados de perfis. Consumido apenas pelo proprio modulo.

`AthleteProfileRecord` existe para que o service nunca receba um objeto ORM: e o que
permite substituir esta implementacao por uma fake em dicionario nos testes unitarios.
"""
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any, Optional, Protocol

from sqlmodel import Session, func, select

from app.modules.clips.models import Clip, ProcessingJob, Video
from app.modules.identity.models import User, UserRole
from app.modules.profiles.models import (
    AthleteProfile,
    AthleteStatus,
    DominantFoot,
    Position,
)


@dataclass(frozen=True)
class AthleteProfileRecord:
    """Perfil do atleta somado aos dados de identidade, sem acoplamento com ORM."""

    user_id: uuid.UUID
    first_name: str
    last_name: str
    position: Optional[Position]
    birth_date: Optional[date]
    height_cm: Optional[int]
    dominant_foot: Optional[DominantFoot]
    state: Optional[str]
    city: Optional[str]
    current_club: Optional[str]
    bio: Optional[str]
    avatar_path: Optional[str]
    status: AthleteStatus


class AthleteProfileRepository(Protocol):
    def get_by_user_id(self, user_id: uuid.UUID) -> Optional[AthleteProfileRecord]: ...

    def count_clips(self, user_id: uuid.UUID) -> int: ...

    def update(
        self, user_id: uuid.UUID, changes: dict[str, Any]
    ) -> Optional[AthleteProfileRecord]: ...


class SqlAthleteProfileRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_user_id(self, user_id: uuid.UUID) -> Optional[AthleteProfileRecord]:
        linha = self.session.exec(
            select(User, AthleteProfile)
            .join(AthleteProfile, AthleteProfile.user_id == User.id)
            .where(User.id == user_id)
            .where(User.role == UserRole.ATHLETE)
        ).first()

        if linha is None:
            return None

        user, perfil = linha
        return self._to_record(user, perfil)

    def count_clips(self, user_id: uuid.UUID) -> int:
        total = self.session.exec(
            select(func.count(Clip.id))
            .join(ProcessingJob, Clip.job_id == ProcessingJob.id)
            .join(Video, ProcessingJob.video_id == Video.id)
            .where(Video.user_id == user_id)
        ).one()
        return int(total)

    def update(
        self, user_id: uuid.UUID, changes: dict[str, Any]
    ) -> Optional[AthleteProfileRecord]:
        perfil = self.session.get(AthleteProfile, user_id)
        if perfil is None:
            return None

        for campo, valor in changes.items():
            setattr(perfil, campo, valor)

        # O chamador e dono da transacao (mesma convencao de `get_session` e do handler de
        # `register`): so flush + refresh aqui, sem commit. Nao "ajude" adicionando um commit
        # de volta -- quem chama update() decide quando fechar a transacao.
        self.session.add(perfil)
        self.session.flush()
        self.session.refresh(perfil)

        user = self.session.get(User, user_id)
        return self._to_record(user, perfil)

    @staticmethod
    def _to_record(user: User, perfil: AthleteProfile) -> AthleteProfileRecord:
        return AthleteProfileRecord(
            user_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            position=perfil.position,
            birth_date=perfil.birth_date,
            height_cm=perfil.height_cm,
            dominant_foot=perfil.dominant_foot,
            state=perfil.state,
            city=perfil.city,
            current_club=perfil.current_club,
            bio=perfil.bio,
            avatar_path=perfil.avatar_path,
            status=perfil.status,
        )
