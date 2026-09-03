"""
Regra de negocio de perfis. Unico ponto de entrada para outros modulos (regra D3).
Nao conhece HTTP nem sessao de banco.
"""
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable, Optional

from sqlmodel import Session

from app.core.exceptions import NotFoundError
from app.modules.profiles.models import AthleteStatus, DominantFoot, Position
from app.modules.profiles.repository import (
    AthleteProfileRecord,
    AthleteProfileRepository,
    SqlAthleteProfileRepository,
)


def provision_athlete_profile(session: Session, user_id: uuid.UUID) -> None:
    """
    Cria o perfil vazio de um atleta recem-cadastrado, na transacao do chamador.

    Ponto de entrada D3 para o modulo `identity`: `register()` precisa que o `User` e o
    `AthleteProfile` nasçam na mesma transacao (por isso recebe a `Session` do chamador em
    vez de abrir a sua), mas nao pode importar `profiles.models`/`profiles.repository`
    diretamente. Esta funcao e o unico ponto de acoplamento entre os dois modulos: constroi
    o repositorio e delega, mantendo `AthleteProfile` dentro de `profiles`.
    """
    SqlAthleteProfileRepository(session).create(user_id)


@dataclass(frozen=True)
class AthleteProfileView:
    """O que o mundo externo enxerga de um perfil, com a idade ja derivada."""

    user_id: uuid.UUID
    first_name: str
    last_name: str
    position: Optional[Position]
    age: Optional[int]
    height_cm: Optional[int]
    dominant_foot: Optional[DominantFoot]
    state: Optional[str]
    city: Optional[str]
    current_club: Optional[str]
    bio: Optional[str]
    avatar_path: Optional[str]
    status: AthleteStatus
    clips_count: int


def calcular_idade(nascimento: date, hoje: date) -> int:
    """Idade em anos completos."""
    aniversario_passou = (hoje.month, hoje.day) >= (nascimento.month, nascimento.day)
    return hoje.year - nascimento.year - (0 if aniversario_passou else 1)


class ProfilesService:
    def __init__(
        self,
        repository: AthleteProfileRepository,
        hoje: Callable[[], date] = date.today,
    ):
        self.repository = repository
        self.hoje = hoje

    def get_athlete_profile(self, user_id: uuid.UUID) -> AthleteProfileView:
        record = self.repository.get_by_user_id(user_id)
        if record is None:
            raise NotFoundError("Atleta nao encontrado.")
        return self._to_view(record, self.repository.count_clips(user_id))

    def update_athlete_profile(
        self, user_id: uuid.UUID, changes: dict[str, Any]
    ) -> AthleteProfileView:
        record = self.repository.update(user_id, changes)
        if record is None:
            raise NotFoundError("Atleta nao encontrado.")
        return self._to_view(record, self.repository.count_clips(user_id))

    def _to_view(self, record: AthleteProfileRecord, clips_count: int) -> AthleteProfileView:
        idade = (
            calcular_idade(record.birth_date, self.hoje())
            if record.birth_date is not None
            else None
        )
        return AthleteProfileView(
            user_id=record.user_id,
            first_name=record.first_name,
            last_name=record.last_name,
            position=record.position,
            age=idade,
            height_cm=record.height_cm,
            dominant_foot=record.dominant_foot,
            state=record.state,
            city=record.city,
            current_club=record.current_club,
            bio=record.bio,
            avatar_path=record.avatar_path,
            status=record.status,
            clips_count=clips_count,
        )
