"""
HTTP do modulo de perfis: rota, validacao e serializacao. Sem regra de negocio.
Erros sobem como excecao de dominio e sao traduzidos pelo handler unico do main.py.
"""
import uuid
from dataclasses import dataclass
from typing import Any, Callable

import pydantic
from fastapi import APIRouter, Body, Depends, File, UploadFile
from pydantic import BaseModel
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_user
from app.core.exceptions import ValidationError
from app.core.storage import StorageBackend, get_storage
from app.modules.identity.models import User, UserRole
from app.modules.profiles.repository import (
    SqlAthleteProfileRepository,
    SqlClubProfileRepository,
    SqlScoutProfileRepository,
)
from app.modules.profiles.schemas import (
    AthleteProfileOwnerResponse,
    AthleteProfileResponse,
    AthleteProfileUpdate,
    ClubProfileResponse,
    ClubProfileUpdate,
    MyProfileResponse,
    OwnerProfileResponse,
    ScoutProfileResponse,
    ScoutProfileUpdate,
)
from app.modules.profiles.service import (
    TAMANHO_MAXIMO_DE_AVATAR,
    AvatarService,
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


def get_avatar_service(
    storage: StorageBackend = Depends(get_storage),
) -> AvatarService:
    return AvatarService(storage)


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
    resposta: Callable[[Any], OwnerProfileResponse]


_POR_PAPEL: dict[UserRole, _Papel] = {
    UserRole.ATHLETE: _Papel(
        servico=get_service,
        ler=lambda svc, uid: svc.get_athlete_profile(uid),
        atualizar=lambda svc, uid, ch: svc.update_athlete_profile(uid, ch),
        schema_update=AthleteProfileUpdate,
        # Variante do dono (traz `birth_date`): `/me` e os endpoints de avatar so
        # atendem o proprio autenticado, nunca um perfil alheio.
        resposta=AthleteProfileOwnerResponse.from_view,
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


# ---------------------------------------------------------------------------
# Avatar: um endpoint para os três papéis (decisão E4)
# ---------------------------------------------------------------------------

@router.post("/me/avatar", response_model=MyProfileResponse)
async def upload_my_avatar(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    avatares: AvatarService = Depends(get_avatar_service),
):
    """
    Grava o avatar do autenticado e devolve o perfil no formato de `GET /profiles/me`.

    O papel vem do JWT, como no `PUT /me`: nada na URL diz se é atleta, scout ou clube.
    """
    papel = _papel_de(current_user)
    servico = papel.servico(session)

    # Ler antes de gravar faz duas coisas: dá o 404 de quem não tem perfil do próprio
    # papel sem deixar arquivo órfão em disco, e é a única chance de descobrir qual era
    # o avatar anterior -- depois do update ele já foi sobrescrito.
    anterior = papel.ler(servico, current_user.id).avatar_path

    # Um byte além do limite já basta para o `salvar` recusar, então não há motivo para
    # trazer um envio gigante inteiro para a memória. A regra de tamanho continua sendo
    # do AvatarService; aqui isso é só o teto da leitura.
    conteudo = await file.read(TAMANHO_MAXIMO_DE_AVATAR + 1)
    novo = avatares.salvar(current_user.id, conteudo, file.content_type)

    view = papel.atualizar(servico, current_user.id, {"avatar_path": novo})
    resposta = MyProfileResponse(role=current_user.role, profile=papel.resposta(view))
    # O repositório só faz flush (a transação é do chamador), como no `PUT /me`.
    session.commit()

    # Só depois do commit: apagar antes deixaria o perfil apontando para um arquivo que
    # não existe mais se a transação falhasse. E só quando o caminho mudou -- trocar um
    # JPEG por outro JPEG reaproveita a mesma chave, e apagá-la removeria o arquivo
    # recém-gravado.
    if anterior != novo:
        avatares.remover(anterior)

    return resposta


@router.delete("/me/avatar", status_code=204)
def delete_my_avatar(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    avatares: AvatarService = Depends(get_avatar_service),
):
    """
    Remove o avatar do autenticado. Idempotente: sem avatar, 204 do mesmo jeito.

    404 continua valendo para quem não tem perfil do próprio papel -- é inconsistência
    de cadastro, não ausência de avatar.
    """
    papel = _papel_de(current_user)
    servico = papel.servico(session)

    anterior = papel.ler(servico, current_user.id).avatar_path
    if anterior is None:
        return None

    papel.atualizar(servico, current_user.id, {"avatar_path": None})
    session.commit()
    avatares.remover(anterior)
    return None
