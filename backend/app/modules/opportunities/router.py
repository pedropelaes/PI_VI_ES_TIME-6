"""
Peneiras (oportunidades) e inscrições.
Spec: docs/superpowers/specs/2026-11-11-oportunidades-peneiras-design.md

Ordem importa: rotas de caminho fixo de um segmento (`/mine`) ficam ACIMA de
`/{opportunity_id}`, senão "mine" é lido como UUID e vira 422.
"""
import uuid
from datetime import datetime, timezone
from typing import Callable

from fastapi import APIRouter, Depends, Response
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_user
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.modules.identity.models import User, UserRole
from app.modules.opportunities.models import ApplicationStatus, Opportunity
from app.modules.opportunities.repository import OpportunityRepository
from app.modules.opportunities.schemas import (
    Eligibility,
    MyApplication,
    OpportunityCreate,
    OpportunityDetail,
    OpportunityUpdate,
    Organizer,
)
from app.modules.opportunities.service import (
    esta_aberta,
    motivo_inelegivel,
    validar_e_normalizar,
)
from app.modules.profiles.models import Position

router = APIRouter(prefix="/opportunities", tags=["opportunities"])

ORGANIZADORES = (UserRole.CLUB, UserRole.SCOUT)


def get_repository(session: Session = Depends(get_session)) -> OpportunityRepository:
    return OpportunityRepository(session)


def get_now() -> Callable[[], datetime]:
    """Separado para os testes conseguirem fixar o 'agora'."""
    return lambda: datetime.now(timezone.utc)


# --- helpers -----------------------------------------------------------------------

def _exige_organizador(user: User) -> None:
    if user.role not in ORGANIZADORES:
        raise ForbiddenError("Só clubes e scouts podem gerenciar peneiras.")


def _exige_atleta(user: User) -> None:
    if user.role != UserRole.ATHLETE:
        raise ForbiddenError("Só atletas podem se inscrever em peneiras.")


def _busca(repo: OpportunityRepository, opp_id: uuid.UUID, lock: bool = False) -> Opportunity:
    opp = repo.get(opp_id, lock=lock)
    if opp is None:
        raise NotFoundError("Peneira não encontrada.")
    return opp


def _da_minha_autoria(
    repo: OpportunityRepository, opp_id: uuid.UUID, user: User, lock: bool = False
) -> Opportunity:
    _exige_organizador(user)
    opp = _busca(repo, opp_id, lock)
    if opp.organizer_id != user.id:
        raise ForbiddenError("Esta peneira não é sua.")
    return opp


def _aplica(opp: Opportunity, dados: dict) -> None:
    """Copia o payload para o model e valida o resultado (vale para criar e editar)."""
    if "positions" in dados:
        dados["positions"] = sorted({Position(p).value for p in dados["positions"] or []})
    for campo, valor in dados.items():
        setattr(opp, campo, valor)
    validar_e_normalizar(opp)


def _resumo(opp: Opportunity, organizador: User, ocupadas: int, avatar_url=None) -> dict:
    return dict(
        id=opp.id,
        title=opp.title,
        mode=opp.mode,
        state=opp.state,
        city=opp.city,
        event_at=opp.event_at,
        registration_deadline=opp.registration_deadline,
        min_age=opp.min_age,
        max_age=opp.max_age,
        positions=opp.positions,
        spots_left=(
            None if opp.max_applications is None else max(opp.max_applications - ocupadas, 0)
        ),
        is_cancelled=opp.cancelled_at is not None,
        organizer=Organizer(
            user_id=organizador.id,
            first_name=organizador.first_name,
            last_name=organizador.last_name,
            role=organizador.role,
            avatar_url=avatar_url,
        ),
    )


def _detalhe(
    repo: OpportunityRepository, opp: Opportunity, user: User, agora: datetime
) -> OpportunityDetail:
    organizador = repo.session.get(User, opp.organizer_id)
    ocupadas = repo.occupied(opp.id)

    minha = elegibilidade = None
    # O link da reunião é o acesso à avaliação: só dono e inscrito aprovado veem (spec D7).
    ve_link = user.id == opp.organizer_id
    if user.role == UserRole.ATHLETE:
        inscricao = repo.get_application(opp.id, user.id)
        if inscricao is not None:
            minha = MyApplication(status=inscricao.status)
            ve_link = inscricao.status == ApplicationStatus.APROVADA
        motivo = motivo_inelegivel(opp, repo.athlete_profile(user.id), agora.date())
        elegibilidade = Eligibility(eligible=motivo is None, reason=motivo)

    return OpportunityDetail(
        **_resumo(opp, organizador, ocupadas, repo.organizer_avatar(organizador)),
        description=opp.description,
        address=opp.address,
        meeting_url=opp.meeting_url if ve_link else None,
        max_applications=opp.max_applications,
        is_open=esta_aberta(opp, ocupadas, agora),
        cancelled_at=opp.cancelled_at,
        my_application=minha,
        eligibility=elegibilidade,
    )


# --- organizador -------------------------------------------------------------------

@router.post("", status_code=201, response_model=OpportunityDetail)
def create_opportunity(
    payload: OpportunityCreate,
    current_user: User = Depends(get_current_user),
    repo: OpportunityRepository = Depends(get_repository),
    now: Callable[[], datetime] = Depends(get_now),
):
    _exige_organizador(current_user)
    opp = Opportunity(organizer_id=current_user.id)
    _aplica(opp, payload.model_dump())
    repo.session.add(opp)
    repo.session.commit()
    repo.session.refresh(opp)
    return _detalhe(repo, opp, current_user, now())


@router.get("/{opportunity_id}", response_model=OpportunityDetail)
def get_opportunity(
    opportunity_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    repo: OpportunityRepository = Depends(get_repository),
    now: Callable[[], datetime] = Depends(get_now),
):
    return _detalhe(repo, _busca(repo, opportunity_id), current_user, now())


@router.patch("/{opportunity_id}", response_model=OpportunityDetail)
def update_opportunity(
    opportunity_id: uuid.UUID,
    payload: OpportunityUpdate,
    current_user: User = Depends(get_current_user),
    repo: OpportunityRepository = Depends(get_repository),
    now: Callable[[], datetime] = Depends(get_now),
):
    opp = _da_minha_autoria(repo, opportunity_id, current_user, lock=True)
    if opp.cancelled_at is not None:
        raise ConflictError("Peneira cancelada não pode ser editada.")
    _aplica(opp, payload.model_dump(exclude_unset=True))
    if opp.max_applications is not None and opp.max_applications < repo.occupied(opp.id):
        raise ConflictError("O número de vagas não pode ficar abaixo das inscrições ativas.")
    repo.session.commit()
    repo.session.refresh(opp)
    return _detalhe(repo, opp, current_user, now())


@router.post("/{opportunity_id}/cancel", response_model=OpportunityDetail)
def cancel_opportunity(
    opportunity_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    repo: OpportunityRepository = Depends(get_repository),
    now: Callable[[], datetime] = Depends(get_now),
):
    opp = _da_minha_autoria(repo, opportunity_id, current_user)
    if opp.cancelled_at is None:
        opp.cancelled_at = now()
        repo.session.commit()
        repo.session.refresh(opp)
    return _detalhe(repo, opp, current_user, now())


@router.delete("/{opportunity_id}", status_code=204)
def delete_opportunity(
    opportunity_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    repo: OpportunityRepository = Depends(get_repository),
):
    opp = _da_minha_autoria(repo, opportunity_id, current_user)
    repo.delete(opp.id)
    repo.session.commit()
    return Response(status_code=204)
