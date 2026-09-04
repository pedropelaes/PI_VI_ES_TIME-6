"""
Regra de negocio de perfis. Unico ponto de entrada para outros modulos (regra D3).
Nao conhece HTTP nem sessao de banco.
"""
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable, List, Optional

from sqlmodel import Session

from app.core.exceptions import NotFoundError
from app.modules.identity.models import UserRole
from app.modules.profiles.models import AthleteStatus, DominantFoot, Position
from app.modules.profiles.repository import (
    AthleteProfileRecord,
    AthleteProfileRepository,
    ClubProfileRecord,
    ClubProfileRepository,
    ScoutProfileRecord,
    ScoutProfileRepository,
    SqlAthleteProfileRepository,
    SqlClubProfileRepository,
    SqlScoutProfileRepository,
)

# Qual repositorio cria o perfil de cada papel. Um papel novo sem entrada aqui estoura
# no `provision_profile` em vez de cadastrar um usuario sem perfil -- estado invalido
# que a secao 1 da spec descreve.
_REPOSITORIO_POR_PAPEL = {
    UserRole.ATHLETE: SqlAthleteProfileRepository,
    UserRole.SCOUT: SqlScoutProfileRepository,
    UserRole.CLUB: SqlClubProfileRepository,
}


def provision_profile(session: Session, user_id: uuid.UUID, role: UserRole) -> None:
    """
    Cria o perfil vazio do papel de um usuario recem-cadastrado, na transacao do chamador.

    Ponto de entrada D3 para o modulo `identity`: `register()` precisa que o `User` e o
    perfil nascam na mesma transacao (por isso recebe a `Session` do chamador em vez de
    abrir a sua), mas nao pode importar `profiles.models`/`profiles.repository`
    diretamente. Esta funcao e o unico ponto de acoplamento entre os dois modulos: escolhe
    o repositorio do papel e delega, mantendo as tabelas de perfil dentro de `profiles`.
    """
    try:
        repositorio = _REPOSITORIO_POR_PAPEL[role]
    except KeyError:  # pragma: no cover - so alcancavel adicionando um papel novo
        raise NotImplementedError(f"Papel sem tabela de perfil: {role}")

    repositorio(session).create(user_id)


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


@dataclass(frozen=True)
class ScoutProfileView:
    """O que o mundo externo enxerga de um perfil de scout."""

    user_id: uuid.UUID
    first_name: str
    last_name: str
    organization: Optional[str]
    credential: Optional[str]
    state: Optional[str]
    city: Optional[str]
    bio: Optional[str]
    avatar_path: Optional[str]


class ScoutProfilesService:
    """
    Espelha `ProfilesService` para o papel SCOUT.

    Nao ha nada derivado aqui (scout nao tem `age` nem `clips_count`, secao 4.1), mas a
    View existe pelo mesmo motivo do atleta: o router nunca toca em `Record`, entao o
    formato de leitura pode mudar sem arrastar a camada HTTP para dentro do repositorio.
    """

    def __init__(self, repository: ScoutProfileRepository):
        self.repository = repository

    def get_scout_profile(self, user_id: uuid.UUID) -> ScoutProfileView:
        record = self.repository.get_by_user_id(user_id)
        if record is None:
            raise NotFoundError("Scout nao encontrado.")
        return self._to_view(record)

    def update_scout_profile(
        self, user_id: uuid.UUID, changes: dict[str, Any]
    ) -> ScoutProfileView:
        record = self.repository.update(user_id, changes)
        if record is None:
            raise NotFoundError("Scout nao encontrado.")
        return self._to_view(record)

    @staticmethod
    def _to_view(record: ScoutProfileRecord) -> ScoutProfileView:
        return ScoutProfileView(
            user_id=record.user_id,
            first_name=record.first_name,
            last_name=record.last_name,
            organization=record.organization,
            credential=record.credential,
            state=record.state,
            city=record.city,
            bio=record.bio,
            avatar_path=record.avatar_path,
        )


@dataclass(frozen=True)
class ClubProfileView:
    """O que o mundo externo enxerga de um perfil de clube."""

    user_id: uuid.UUID
    first_name: str
    last_name: str
    legal_name: Optional[str]
    cnpj: Optional[str]
    categories: List[str]
    state: Optional[str]
    city: Optional[str]
    bio: Optional[str]
    avatar_path: Optional[str]


class ClubProfilesService:
    """Espelha `ProfilesService` para o papel CLUB."""

    def __init__(self, repository: ClubProfileRepository):
        self.repository = repository

    def get_club_profile(self, user_id: uuid.UUID) -> ClubProfileView:
        record = self.repository.get_by_user_id(user_id)
        if record is None:
            raise NotFoundError("Clube nao encontrado.")
        return self._to_view(record)

    def update_club_profile(
        self, user_id: uuid.UUID, changes: dict[str, Any]
    ) -> ClubProfileView:
        record = self.repository.update(user_id, changes)
        if record is None:
            raise NotFoundError("Clube nao encontrado.")
        return self._to_view(record)

    @staticmethod
    def _to_view(record: ClubProfileRecord) -> ClubProfileView:
        return ClubProfileView(
            user_id=record.user_id,
            first_name=record.first_name,
            last_name=record.last_name,
            legal_name=record.legal_name,
            cnpj=record.cnpj,
            categories=list(record.categories),
            state=record.state,
            city=record.city,
            bio=record.bio,
            avatar_path=record.avatar_path,
        )
