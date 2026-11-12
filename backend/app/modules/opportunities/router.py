"""
Peneiras (oportunidades) e inscrições.
Spec: docs/superpowers/specs/2026-11-11-oportunidades-peneiras-design.md

Ordem importa: rotas de caminho fixo de um segmento (`/mine`) ficam ACIMA de
`/{opportunity_id}`, senão "mine" é lido como UUID e vira 422.
"""
import base64
import binascii
import uuid
from datetime import datetime, timezone
from typing import Callable, List, Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_user
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.modules.identity.models import User, UserRole
from app.modules.opportunities.models import (
    ApplicationStatus,
    Opportunity,
    OpportunityApplication,
    OpportunityMode,
)
from app.modules.opportunities.repository import ListFilters, OpportunityRepository, ocupadas_de
from app.modules.opportunities.schemas import (
    Applicant,
    ApplicationCounts,
    ApplicationOut,
    ApplicationStatusUpdate,
    Eligibility,
    MyApplication,
    MyApplicationItem,
    MyOpportunity,
    OpportunityCreate,
    OpportunityDetail,
    OpportunityPage,
    OpportunitySummary,
    OpportunityUpdate,
    Organizer,
)
from app.modules.opportunities.service import (
    esta_aberta,
    motivo_inelegivel,
    validar_e_normalizar,
)
from app.modules.profiles.models import Position
from app.modules.profiles.service import calcular_idade

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


def _encode_cursor(opp: Opportunity) -> str:
    bruto = f"{opp.event_at.isoformat()}|{opp.id}"
    return base64.urlsafe_b64encode(bruto.encode()).decode()


def _decode_cursor(cursor: Optional[str]) -> Optional[tuple[datetime, uuid.UUID]]:
    if not cursor:
        return None
    try:
        quando, opp_id = base64.urlsafe_b64decode(cursor.encode()).decode().split("|")
        return datetime.fromisoformat(quando), uuid.UUID(opp_id)
    except (ValueError, binascii.Error, UnicodeDecodeError):
        raise ValidationError("Cursor inválido.")


# --- leitura -----------------------------------------------------------------------

@router.get("", response_model=OpportunityPage)
def list_opportunities(
    mode: Optional[OpportunityMode] = None,
    state: Optional[str] = Query(None, min_length=2, max_length=2),
    position: Optional[Position] = None,
    eligible: bool = False,
    q: Optional[str] = Query(None, max_length=100),
    cursor: Optional[str] = None,
    limit: int = Query(12, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    repo: OpportunityRepository = Depends(get_repository),
    now: Callable[[], datetime] = Depends(get_now),
):
    agora = now()
    idade = posicao = None
    if eligible:
        if current_user.role != UserRole.ATHLETE:
            raise ValidationError("O filtro de elegíveis é só para atletas.")
        perfil = repo.athlete_profile(current_user.id)
        if perfil is not None:
            posicao = perfil.position
            if perfil.birth_date is not None:
                idade = calcular_idade(perfil.birth_date, agora.date())

    filtros = ListFilters(
        mode=mode,
        state=state.upper() if state else None,
        position=position,
        query=(q or "").strip() or None,
        only_eligible=eligible,
        athlete_age=idade,
        athlete_position=posicao,
    )
    # Busca 1 a mais para saber se existe próxima página
    linhas = repo.list_open(filtros, agora, limit + 1, after=_decode_cursor(cursor))
    tem_mais = len(linhas) > limit
    linhas = linhas[:limit]

    return OpportunityPage(
        items=[OpportunitySummary(**_resumo(o, u, ocupadas)) for o, u, ocupadas in linhas],
        next_cursor=_encode_cursor(linhas[-1][0]) if tem_mais else None,
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


@router.get("/mine", response_model=List[MyOpportunity])
def my_opportunities(
    current_user: User = Depends(get_current_user),
    repo: OpportunityRepository = Depends(get_repository),
    now: Callable[[], datetime] = Depends(get_now),
):
    _exige_organizador(current_user)
    agora = now()
    opps = repo.list_by_organizer(current_user.id)
    contagens = repo.counts_by_status([opp.id for opp in opps])

    resposta = []
    for opp in opps:
        c = contagens.get(opp.id, {})
        counts = ApplicationCounts(
            pendente=c.get(ApplicationStatus.PENDENTE, 0),
            aprovada=c.get(ApplicationStatus.APROVADA, 0),
            recusada=c.get(ApplicationStatus.RECUSADA, 0),
        )
        ocupadas = ocupadas_de(c)
        resposta.append(
            MyOpportunity(
                **_resumo(opp, current_user, ocupadas),
                is_open=esta_aberta(opp, ocupadas, agora),
                counts=counts,
            )
        )
    return resposta


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


# --- atleta ------------------------------------------------------------------------

@router.post("/{opportunity_id}/apply", status_code=201, response_model=ApplicationOut)
def apply(
    opportunity_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    repo: OpportunityRepository = Depends(get_repository),
    now: Callable[[], datetime] = Depends(get_now),
):
    _exige_atleta(current_user)
    # FOR UPDATE: duas inscrições simultâneas não ocupam a mesma última vaga.
    opp = _busca(repo, opportunity_id, lock=True)
    agora = now()

    if repo.get_application(opp.id, current_user.id) is not None:
        raise ConflictError("Você já está inscrito nesta peneira.")
    if opp.cancelled_at is not None or opp.registration_deadline < agora:
        raise ConflictError("As inscrições desta peneira estão encerradas.")
    if opp.max_applications is not None and repo.occupied(opp.id) >= opp.max_applications:
        raise ConflictError("Vagas esgotadas.")
    motivo = motivo_inelegivel(opp, repo.athlete_profile(current_user.id), agora.date())
    if motivo is not None:
        raise ValidationError(motivo)

    inscricao = OpportunityApplication(opportunity_id=opp.id, athlete_id=current_user.id)
    repo.session.add(inscricao)
    repo.session.commit()
    return ApplicationOut(
        opportunity_id=opp.id, athlete_id=current_user.id, status=inscricao.status
    )


@router.delete("/{opportunity_id}/apply", status_code=204)
def cancel_application(
    opportunity_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    repo: OpportunityRepository = Depends(get_repository),
):
    _exige_atleta(current_user)
    _busca(repo, opportunity_id, lock=True)  # serializa com aprovar/recusar do organizador
    inscricao = repo.get_application(opportunity_id, current_user.id)
    if inscricao is None:
        raise NotFoundError("Você não está inscrito nesta peneira.")
    if inscricao.status != ApplicationStatus.PENDENTE:
        raise ConflictError("Só dá para cancelar inscrição ainda em análise.")
    repo.session.delete(inscricao)
    repo.session.commit()
    return Response(status_code=204)


@router.get("/applications/me", response_model=List[MyApplicationItem])
def my_applications(
    current_user: User = Depends(get_current_user),
    repo: OpportunityRepository = Depends(get_repository),
):
    _exige_atleta(current_user)
    linhas = repo.list_by_athlete(current_user.id)
    contagens = repo.counts_by_status([opp.id for _, opp, _ in linhas])
    return [
        MyApplicationItem(
            status=inscricao.status,
            created_at=inscricao.created_at,
            opportunity=OpportunitySummary(
                **_resumo(opp, organizador, ocupadas_de(contagens.get(opp.id, {})))
            ),
        )
        for inscricao, opp, organizador in linhas
    ]


# --- gestão de inscritos (dono) ----------------------------------------------------

@router.get("/{opportunity_id}/applications", response_model=List[Applicant])
def list_applications(
    opportunity_id: uuid.UUID,
    status: Optional[ApplicationStatus] = None,
    current_user: User = Depends(get_current_user),
    repo: OpportunityRepository = Depends(get_repository),
    now: Callable[[], datetime] = Depends(get_now),
):
    opp = _da_minha_autoria(repo, opportunity_id, current_user)
    hoje = now().date()
    return [
        Applicant(
            athlete_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            avatar_url=perfil.avatar_path if perfil else None,
            position=perfil.position if perfil else None,
            age=calcular_idade(perfil.birth_date, hoje) if perfil and perfil.birth_date else None,
            city=perfil.city if perfil else None,
            state=perfil.state if perfil else None,
            status=inscricao.status,
            created_at=inscricao.created_at,
        )
        for inscricao, user, perfil in repo.list_applicants(opp.id, status)
    ]


@router.patch("/{opportunity_id}/applications/{athlete_id}", response_model=ApplicationOut)
def set_application_status(
    opportunity_id: uuid.UUID,
    athlete_id: uuid.UUID,
    payload: ApplicationStatusUpdate,
    current_user: User = Depends(get_current_user),
    repo: OpportunityRepository = Depends(get_repository),
):
    # Permitido depois do prazo: a avaliação acontece depois das inscrições.
    opp = _da_minha_autoria(repo, opportunity_id, current_user, lock=True)
    if opp.cancelled_at is not None:
        raise ConflictError("Peneira cancelada.")
    if payload.status == ApplicationStatus.PENDENTE:
        raise ValidationError("Use APROVADA ou RECUSADA.")
    inscricao = repo.get_application(opp.id, athlete_id)
    if inscricao is None:
        raise NotFoundError("Inscrição não encontrada.")

    # Recusada não ocupa vaga; voltar a aprovar precisa de vaga livre.
    volta_a_ocupar = (
        inscricao.status == ApplicationStatus.RECUSADA
        and payload.status == ApplicationStatus.APROVADA
    )
    if (
        volta_a_ocupar
        and opp.max_applications is not None
        and repo.occupied(opp.id) >= opp.max_applications
    ):
        raise ConflictError("Vagas esgotadas.")

    inscricao.status = payload.status
    repo.session.commit()
    return ApplicationOut(opportunity_id=opp.id, athlete_id=athlete_id, status=inscricao.status)
