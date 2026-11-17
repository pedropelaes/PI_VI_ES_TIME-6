"""
GET    /feed                       -> página do feed, com filtros e cursor
POST   /feed/clips/{clip_id}/like  -> curtir
DELETE /feed/clips/{clip_id}/like  -> descurtir
"""
import base64
import binascii
import uuid
from datetime import date, datetime
from typing import Callable, Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError, ValidationError
from app.modules.feed.repository import FeedFilters, FeedRepository, FeedRow
from app.modules.feed.schemas import FeedAthlete, FeedItem, FeedPage, LikeState
from app.modules.identity.models import User
from app.modules.profiles.models import AthleteStatus, Position
from app.modules.profiles.service import calcular_idade

router = APIRouter(prefix="/feed", tags=["feed"])


def get_repository(session: Session = Depends(get_session)) -> FeedRepository:
    return FeedRepository(session)


def get_today() -> Callable[[], date]:
    """Separado para os testes conseguirem fixar o 'hoje'."""
    return date.today


@router.get("", response_model=FeedPage)
def get_feed(
    position: Optional[Position] = None,
    status: Optional[AthleteStatus] = None,
    min_age: Optional[int] = Query(None, ge=0, le=100),
    max_age: Optional[int] = Query(None, ge=0, le=100),
    q: Optional[str] = Query(None, max_length=100),
    cursor: Optional[str] = None,
    limit: int = Query(12, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    repo: FeedRepository = Depends(get_repository),
    today: Callable[[], date] = Depends(get_today),
):
    if min_age is not None and max_age is not None and min_age > max_age:
        raise ValidationError("min_age não pode ser maior que max_age.")

    hoje = today()
    filtros = FeedFilters(
        position=position,
        status=status,
        # idade <= max_age  <=>  nasceu depois de (hoje - (max_age + 1) anos)
        born_after=_anos_atras(hoje, max_age + 1) if max_age is not None else None,
        # idade >= min_age  <=>  nasceu em ou antes de (hoje - min_age anos)
        born_on_or_before=_anos_atras(hoje, min_age) if min_age is not None else None,
        query=(q or "").strip() or None,
    )

    # Busca 1 a mais para saber se existe próxima página
    linhas = repo.list_published(filtros, limit + 1, after=_decode_cursor(cursor))
    tem_mais = len(linhas) > limit
    linhas = linhas[:limit]

    ids = [linha.clip.id for linha in linhas]
    curtidas = repo.like_counts(ids)
    minhas = repo.liked_by(current_user.id, ids)

    return FeedPage(
        items=[_to_item(l, curtidas.get(l.clip.id, 0), l.clip.id in minhas, hoje) for l in linhas],
        next_cursor=_encode_cursor(linhas[-1]) if tem_mais else None,
    )


@router.post("/clips/{clip_id}/like", response_model=LikeState)
def like_clip(
    clip_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    repo: FeedRepository = Depends(get_repository),
):
    return _set_like(repo, current_user, clip_id, liked=True)


@router.delete("/clips/{clip_id}/like", response_model=LikeState)
def unlike_clip(
    clip_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    repo: FeedRepository = Depends(get_repository),
):
    return _set_like(repo, current_user, clip_id, liked=False)


def _set_like(repo: FeedRepository, user: User, clip_id: uuid.UUID, liked: bool) -> LikeState:
    if repo.get_published_clip(clip_id) is None:
        raise NotFoundError("Clipe não encontrado no feed.")

    if liked:
        repo.add_like(user.id, clip_id)
    else:
        repo.remove_like(user.id, clip_id)
    repo.session.commit()

    return LikeState(
        clip_id=clip_id,
        like_count=repo.like_counts([clip_id]).get(clip_id, 0),
        liked_by_me=liked,
    )


def _to_item(linha: FeedRow, like_count: int, liked_by_me: bool, hoje: date) -> FeedItem:
    perfil = linha.profile
    clip = linha.clip
    return FeedItem(
        id=clip.id,
        file_url=linha.file_url,
        duration_seconds=round(clip.end_timestamp - clip.start_timestamp, 2),
        published_at=clip.published_at,
        like_count=like_count,
        liked_by_me=liked_by_me,
        athlete=FeedAthlete(
            user_id=linha.user.id,
            first_name=linha.user.first_name,
            last_name=linha.user.last_name,
            avatar_url=perfil.avatar_path,
            position=perfil.position,
            age=calcular_idade(perfil.birth_date, hoje) if perfil.birth_date else None,
            city=perfil.city,
            state=perfil.state,
            status=perfil.status,
        ),
    )


def _anos_atras(hoje: date, anos: int) -> date:
    try:
        return hoje.replace(year=hoje.year - anos)
    except ValueError:  # 29/02 em ano não bissexto
        return hoje.replace(year=hoje.year - anos, day=28)


def _encode_cursor(linha: FeedRow) -> str:
    bruto = f"{linha.clip.published_at.isoformat()}|{linha.clip.id}"
    return base64.urlsafe_b64encode(bruto.encode()).decode()


def _decode_cursor(cursor: Optional[str]) -> Optional[tuple[datetime, uuid.UUID]]:
    if not cursor:
        return None
    try:
        quando, clip_id = base64.urlsafe_b64decode(cursor.encode()).decode().split("|")
        return datetime.fromisoformat(quando), uuid.UUID(clip_id)
    except (ValueError, binascii.Error, UnicodeDecodeError):
        raise ValidationError("Cursor inválido.")