"""
HTTP do modulo de perfis: rota, validacao e serializacao. Sem regra de negocio.
Erros sobem como excecao de dominio e sao traduzidos pelo handler unico do main.py.
"""
import uuid
from dataclasses import dataclass
from typing import Any, Callable

import pydantic
from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_user
from app.core.exceptions import ValidationError
from app.modules.identity.models import User, UserRole
from app.modules.profiles.repository import (
    SqlAthleteProfileRepository,
    SqlClubProfileRepository,
    SqlScoutProfileRepository,
)
from app.modules.profiles.schemas import (
    AthleteProfileResponse,
    AthleteProfileUpdate,
    ClubProfileResponse,
    ClubProfileUpdate,
    MyProfileResponse,
    ProfileResponse,
    ScoutProfileResponse,
    ScoutProfileUpdate,
)
from app.modules.profiles.service import (
    ClubProfilesService,
    ProfilesService,
    ScoutProfilesService,
)

router = APIRouter(prefix="/profiles", tags=["profiles"])


def get_service(session: Session = Depends(get_session)) -> ProfilesService:
    return ProfilesService(SqlAthleteProfileRepository(session))


def get_scout_service(session: Session = Depends(get_session)) -> ScoutProfilesService:
    return ScoutProfilesService(SqlScoutProfileRepository(session))


def get_club_service(session: Session = Depends(get_session)) -> ClubProfilesService:
    return ClubProfilesService(SqlClubProfileRepository(session))


@router.get("/athletes/{user_id}", response_model=AthleteProfileResponse)
def get_athlete_profile(
    user_id: uuid.UUID,
    service: ProfilesService = Depends(get_service),
    current_user: User = Depends(get_current_user),
):
    """Perfil de um atleta. Exige autenticacao (decisao P2 da spec)."""
    return AthleteProfileResponse.from_view(service.get_athlete_profile(user_id))


@router.get("/scouts/{user_id}", response_model=ScoutProfileResponse)
def get_scout_profile(
    user_id: uuid.UUID,
    service: ScoutProfilesService = Depends(get_scout_service),
    current_user: User = Depends(get_current_user),
):
    """Perfil de um scout. 404 tambem quando o id existe com outro papel (secao 4.1)."""
    return ScoutProfileResponse.from_view(service.get_scout_profile(user_id))


@router.get("/clubs/{user_id}", response_model=ClubProfileResponse)
def get_club_profile(
    user_id: uuid.UUID,
    service: ClubProfilesService = Depends(get_club_service),
    current_user: User = Depends(get_current_user),
):
    """Perfil de um clube. 404 tambem quando o id existe com outro papel (secao 4.1)."""
    return ClubProfileResponse.from_view(service.get_club_profile(user_id))


# ---------------------------------------------------------------------------
# /me polimorfico (decisao Q3): o papel vem do JWT, nao da URL
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _Papel:
    """Tudo o que `/me` precisa saber para atender um papel."""

    servico: Callable[[Session], Any]
    ler: Callable[[Any, uuid.UUID], Any]
    atualizar: Callable[[Any, uuid.UUID, dict[str, Any]], Any]
    schema_update: type[BaseModel]
    resposta: Callable[[Any], ProfileResponse]


_POR_PAPEL: dict[UserRole, _Papel] = {
    UserRole.ATHLETE: _Papel(
        servico=get_service,
        ler=lambda svc, uid: svc.get_athlete_profile(uid),
        atualizar=lambda svc, uid, ch: svc.update_athlete_profile(uid, ch),
        schema_update=AthleteProfileUpdate,
        resposta=AthleteProfileResponse.from_view,
    ),
    UserRole.SCOUT: _Papel(
        servico=get_scout_service,
        ler=lambda svc, uid: svc.get_scout_profile(uid),
        atualizar=lambda svc, uid, ch: svc.update_scout_profile(uid, ch),
        schema_update=ScoutProfileUpdate,
        resposta=ScoutProfileResponse.from_view,
    ),
    UserRole.CLUB: _Papel(
        servico=get_club_service,
        ler=lambda svc, uid: svc.get_club_profile(uid),
        atualizar=lambda svc, uid, ch: svc.update_club_profile(uid, ch),
        schema_update=ClubProfileUpdate,
        resposta=ClubProfileResponse.from_view,
    ),
}


def _papel_de(user: User) -> _Papel:
    ligacao = _POR_PAPEL.get(user.role)
    if ligacao is None:  # pragma: no cover - so alcancavel adicionando um papel novo
        raise NotImplementedError(f"Papel sem perfil: {user.role}")
    return ligacao


@router.get("/me", response_model=MyProfileResponse)
def get_my_profile(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Proprio perfil, no formato `{ role, profile }` da decisao Q4."""
    papel = _papel_de(current_user)
    view = papel.ler(papel.servico(session), current_user.id)
    return MyProfileResponse(role=current_user.role, profile=papel.resposta(view))


@router.put("/me", response_model=MyProfileResponse)
def update_my_profile(
    payload: dict[str, Any] = Body(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Atualizacao parcial do perfil do autenticado, seja qual for o papel.

    O corpo chega cru porque so da para escolher o schema depois de conhecer o papel --
    que vem do JWT, nao da URL (Q3). A validacao acontece logo abaixo, contra o schema
    daquele papel: um campo de outro papel bate no `extra="forbid"` e vira 422.
    """
    papel = _papel_de(current_user)

    try:
        validado = papel.schema_update.model_validate(payload)
    except pydantic.ValidationError as erro:
        problemas = "; ".join(
            f"{'.'.join(str(parte) for parte in e['loc']) or 'corpo'}: {e['msg']}"
            for e in erro.errors()
        )
        raise ValidationError(
            f"Dados invalidos para o papel {current_user.role.value}. {problemas}"
        )

    # exclude_unset garante que campos ausentes nao sejam zerados.
    changes = validado.model_dump(exclude_unset=True)
    view = papel.atualizar(papel.servico(session), current_user.id, changes)
    resposta = MyProfileResponse(role=current_user.role, profile=papel.resposta(view))
    # O repositorio so faz flush (a transacao e do chamador); fechar e responsabilidade
    # daqui, senao a alteracao some quando a Session do request e descartada.
    session.commit()
    return resposta
