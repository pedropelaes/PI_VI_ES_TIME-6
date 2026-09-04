"""DTOs de entrada e saida do modulo de perfis."""
import uuid
from datetime import date
from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from app.modules.identity.models import UserRole
from app.modules.profiles.models import (
    AthleteStatus,
    ClubCategory,
    DominantFoot,
    Position,
)
from app.modules.profiles.service import (
    AthleteProfileView,
    ClubProfileView,
    ScoutProfileView,
)


class _PartialUpdate(BaseModel):
    """
    Base das atualizacoes parciais.

    `extra="forbid"` e o que faz `PUT /profiles/me` devolver 422 quando o autenticado
    manda um campo de outro papel (secao 4.2): o router valida o corpo contra o schema
    do papel dele, e um campo desconhecido vira erro em vez de ser ignorado em silencio.
    """

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Atleta
# ---------------------------------------------------------------------------

class AthleteProfileResponse(BaseModel):
    """Perfil do atleta como sai na API. `age` ja vem derivada de birth_date."""

    user_id: uuid.UUID
    first_name: str
    last_name: str
    position: Optional[Position]
    status: AthleteStatus
    age: Optional[int]
    height_cm: Optional[int]
    dominant_foot: Optional[DominantFoot]
    city: Optional[str]
    state: Optional[str]
    current_club: Optional[str]
    bio: Optional[str]
    avatar_url: Optional[str]
    clips_count: int

    @classmethod
    def from_view(cls, view: AthleteProfileView) -> "AthleteProfileResponse":
        return cls(
            user_id=view.user_id,
            first_name=view.first_name,
            last_name=view.last_name,
            position=view.position,
            status=view.status,
            age=view.age,
            height_cm=view.height_cm,
            dominant_foot=view.dominant_foot,
            city=view.city,
            state=view.state,
            current_club=view.current_club,
            bio=view.bio,
            # `avatar_path` e como a coluna se chama; para o cliente e uma URL.
            avatar_url=view.avatar_path,
            clips_count=view.clips_count,
        )


class AthleteProfileUpdate(_PartialUpdate):
    """Atualizacao parcial: apenas os campos enviados sao alterados."""

    position: Optional[Position] = None
    birth_date: Optional[date] = None
    height_cm: Optional[int] = Field(default=None, ge=100, le=250)
    dominant_foot: Optional[DominantFoot] = None
    state: Optional[str] = Field(default=None, min_length=2, max_length=2)
    city: Optional[str] = None
    current_club: Optional[str] = None
    bio: Optional[str] = None
    status: Optional[AthleteStatus] = None


# ---------------------------------------------------------------------------
# Scout
# ---------------------------------------------------------------------------

class ScoutProfileResponse(BaseModel):
    """Perfil do scout como sai na API. Sem `age` nem `clips_count` (secao 4.1)."""

    user_id: uuid.UUID
    first_name: str
    last_name: str
    organization: Optional[str]
    credential: Optional[str]
    city: Optional[str]
    state: Optional[str]
    bio: Optional[str]
    avatar_url: Optional[str]

    @classmethod
    def from_view(cls, view: ScoutProfileView) -> "ScoutProfileResponse":
        return cls(
            user_id=view.user_id,
            first_name=view.first_name,
            last_name=view.last_name,
            organization=view.organization,
            credential=view.credential,
            city=view.city,
            state=view.state,
            bio=view.bio,
            avatar_url=view.avatar_path,
        )


class ScoutProfileUpdate(_PartialUpdate):
    """Atualizacao parcial do perfil de scout."""

    organization: Optional[str] = None
    credential: Optional[str] = None
    state: Optional[str] = Field(default=None, min_length=2, max_length=2)
    city: Optional[str] = None
    bio: Optional[str] = None


# ---------------------------------------------------------------------------
# Clube
# ---------------------------------------------------------------------------

class ClubProfileResponse(BaseModel):
    """Perfil do clube como sai na API. Sem `age` nem `clips_count` (secao 4.1)."""

    user_id: uuid.UUID
    first_name: str
    last_name: str
    legal_name: Optional[str]
    cnpj: Optional[str]
    categories: List[ClubCategory]
    city: Optional[str]
    state: Optional[str]
    bio: Optional[str]
    avatar_url: Optional[str]

    @classmethod
    def from_view(cls, view: ClubProfileView) -> "ClubProfileResponse":
        return cls(
            user_id=view.user_id,
            first_name=view.first_name,
            last_name=view.last_name,
            legal_name=view.legal_name,
            cnpj=view.cnpj,
            categories=view.categories,
            city=view.city,
            state=view.state,
            bio=view.bio,
            avatar_url=view.avatar_path,
        )


class ClubProfileUpdate(_PartialUpdate):
    """
    Atualizacao parcial do perfil de clube.

    `categories` e substituida inteira quando enviada -- nao ha operacao de adicionar ou
    remover uma categoria isolada nesta fatia.
    """

    legal_name: Optional[str] = None
    # Sem validacao de digito verificador nesta fatia (secao 8): so o tamanho da coluna.
    cnpj: Optional[str] = Field(default=None, max_length=14)
    categories: Optional[List[ClubCategory]] = None
    state: Optional[str] = Field(default=None, min_length=2, max_length=2)
    city: Optional[str] = None
    bio: Optional[str] = None


# ---------------------------------------------------------------------------
# /me polimorfico
# ---------------------------------------------------------------------------

ProfileResponse = Union[AthleteProfileResponse, ScoutProfileResponse, ClubProfileResponse]


class MyProfileResponse(BaseModel):
    """
    Formato de `/profiles/me` (decisao Q4): o papel fora, o perfil dentro.

    Os tres Response tem conjuntos de campos obrigatorios disjuntos, entao a uniao nao
    e ambigua -- e o cliente TypeScript consegue estreitar o tipo olhando so `role`.
    """

    role: UserRole
    profile: ProfileResponse
