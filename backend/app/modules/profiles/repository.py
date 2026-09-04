"""
Acesso a dados de perfis. Consumido apenas pelo proprio modulo.

Cada papel tem seu `Record` -- um dataclass congelado com os campos de identidade
(`first_name`, `last_name`) somados aos campos daquele papel. Eles existem para que o
service nunca receba um objeto ORM: e o que permite substituir estas implementacoes por
fakes em dicionario nos testes unitarios.
"""
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any, Generic, List, Optional, Protocol, TypeVar

from sqlmodel import Session, func, select

from app.modules.clips.models import Clip, ProcessingJob, Video
from app.modules.identity.models import User, UserRole
from app.modules.profiles.models import (
    AthleteProfile,
    AthleteStatus,
    ClubProfile,
    DominantFoot,
    Position,
    ScoutProfile,
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
    club_history: Optional[str]
    bio: Optional[str]
    avatar_path: Optional[str]
    status: AthleteStatus


@dataclass(frozen=True)
class ScoutProfileRecord:
    """Perfil do scout somado aos dados de identidade."""

    user_id: uuid.UUID
    first_name: str
    last_name: str
    organization: Optional[str]
    credential: Optional[str]
    state: Optional[str]
    city: Optional[str]
    bio: Optional[str]
    avatar_path: Optional[str]


@dataclass(frozen=True)
class ClubProfileRecord:
    """Perfil do clube somado aos dados de identidade."""

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


class AthleteProfileRepository(Protocol):
    def get_by_user_id(self, user_id: uuid.UUID) -> Optional[AthleteProfileRecord]: ...

    def count_clips(self, user_id: uuid.UUID) -> int: ...

    def update(
        self, user_id: uuid.UUID, changes: dict[str, Any]
    ) -> Optional[AthleteProfileRecord]: ...

    def create(self, user_id: uuid.UUID) -> None: ...


class ScoutProfileRepository(Protocol):
    def get_by_user_id(self, user_id: uuid.UUID) -> Optional[ScoutProfileRecord]: ...

    def update(
        self, user_id: uuid.UUID, changes: dict[str, Any]
    ) -> Optional[ScoutProfileRecord]: ...

    def create(self, user_id: uuid.UUID) -> None: ...


class ClubProfileRepository(Protocol):
    def get_by_user_id(self, user_id: uuid.UUID) -> Optional[ClubProfileRecord]: ...

    def update(
        self, user_id: uuid.UUID, changes: dict[str, Any]
    ) -> Optional[ClubProfileRecord]: ...

    def create(self, user_id: uuid.UUID) -> None: ...


# Parametriza o `Record` que cada repositorio devolve, para que a base compartilhada
# nao apague os tipos das subclasses.
RecordT = TypeVar("RecordT")


class _SqlProfileRepository(Generic[RecordT]):
    """
    O que os tres repositorios fazem igual: buscar pelo par (usuario, papel), criar o
    perfil vazio e aplicar uma atualizacao parcial.

    Cada subclasse declara sua tabela (`modelo`), o papel que filtra (`papel`) e como
    montar seu `Record`. Nada aqui e generico o bastante para virar API publica do
    modulo -- as subclasses e os Protocolos acima e que sao o contrato.
    """

    modelo: type
    papel: UserRole

    def __init__(self, session: Session):
        self.session = session

    def create(self, user_id: uuid.UUID) -> None:
        """
        Cria o perfil vazio de um usuario recem-cadastrado.

        Mesma convencao de `update()`: so `add` + `flush`, sem `commit` -- quem chama
        (`register`, no modulo `identity`) e dono da transacao e decide quando fechar.
        """
        self.session.add(self.modelo(user_id=user_id))
        self.session.flush()

    def get_by_user_id(self, user_id: uuid.UUID) -> Optional[RecordT]:
        """
        Devolve None tanto para id inexistente quanto para id de outro papel: o filtro
        por `User.role` e o que faz `/scouts/{id}` de um atleta virar 404 (secao 4.1).
        """
        linha = self.session.exec(
            select(User, self.modelo)
            .join(self.modelo, self.modelo.user_id == User.id)
            .where(User.id == user_id)
            .where(User.role == self.papel)
        ).first()

        if linha is None:
            return None

        user, perfil = linha
        return self._to_record(user, perfil)

    def update(self, user_id: uuid.UUID, changes: dict[str, Any]) -> Optional[RecordT]:
        perfil = self.session.get(self.modelo, user_id)
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
    def _to_record(user: User, perfil: Any) -> RecordT:  # pragma: no cover - abstrato
        raise NotImplementedError


class SqlAthleteProfileRepository(_SqlProfileRepository[AthleteProfileRecord]):
    modelo = AthleteProfile
    papel = UserRole.ATHLETE

    def count_clips(self, user_id: uuid.UUID) -> int:
        total = self.session.exec(
            select(func.count(Clip.id))
            .join(ProcessingJob, Clip.job_id == ProcessingJob.id)
            .join(Video, ProcessingJob.video_id == Video.id)
            .where(Video.user_id == user_id)
        ).one()
        return int(total)

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
            club_history=perfil.club_history,
            bio=perfil.bio,
            avatar_path=perfil.avatar_path,
            status=perfil.status,
        )


class SqlScoutProfileRepository(_SqlProfileRepository[ScoutProfileRecord]):
    modelo = ScoutProfile
    papel = UserRole.SCOUT

    @staticmethod
    def _to_record(user: User, perfil: ScoutProfile) -> ScoutProfileRecord:
        return ScoutProfileRecord(
            user_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            organization=perfil.organization,
            credential=perfil.credential,
            state=perfil.state,
            city=perfil.city,
            bio=perfil.bio,
            avatar_path=perfil.avatar_path,
        )


class SqlClubProfileRepository(_SqlProfileRepository[ClubProfileRecord]):
    modelo = ClubProfile
    papel = UserRole.CLUB

    @staticmethod
    def _to_record(user: User, perfil: ClubProfile) -> ClubProfileRecord:
        return ClubProfileRecord(
            user_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            legal_name=perfil.legal_name,
            cnpj=perfil.cnpj,
            # Copia defensiva: a lista vem do JSON carregado pela ORM e o Record e
            # congelado -- devolver a referencia deixaria o "frozen" mentir.
            categories=list(perfil.categories or []),
            state=perfil.state,
            city=perfil.city,
            bio=perfil.bio,
            avatar_path=perfil.avatar_path,
        )
