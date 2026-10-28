"""Leitura do feed: junta clipes, usuários e perfis de atleta numa consulta só."""
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, func, select

from app.modules.clips.models import Clip, ClipStatus, ProcessingJob, Video
from app.modules.feed.models import ClipLike
from app.modules.identity.models import User
from app.modules.profiles.models import AthleteProfile, AthleteStatus, Position


@dataclass(frozen=True)
class FeedFilters:
    position: Optional[Position] = None
    status: Optional[AthleteStatus] = None
    born_after: Optional[date] = None
    born_on_or_before: Optional[date] = None
    query: Optional[str] = None


@dataclass(frozen=True)
class FeedRow:
    clip: Clip
    user: User
    profile: AthleteProfile

    @property
    def file_url(self) -> str:
        return f"/uploads/clips/{self.clip.job_id}/{Path(self.clip.storage_path).name}"


class FeedRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_published(
        self,
        filters: FeedFilters,
        limit: int,
        after: Optional[tuple[datetime, uuid.UUID]] = None,
    ) -> List[FeedRow]:
        """
        Clipes publicados, mais novo primeiro. Paginação por cursor sobre
        (published_at, id): não repete nem pula itens no scroll infinito.
        """
        stmt = (
            select(Clip, User, AthleteProfile)
            .join(ProcessingJob, Clip.job_id == ProcessingJob.id)
            .join(Video, ProcessingJob.video_id == Video.id)
            .join(User, Video.user_id == User.id)
            .join(AthleteProfile, AthleteProfile.user_id == User.id)
            .where(Clip.status == ClipStatus.PUBLISHED)
            .where(Clip.storage_path.is_not(None))
            .where(Clip.published_at.is_not(None))
        )

        if filters.position is not None:
            stmt = stmt.where(AthleteProfile.position == filters.position)
        if filters.status is not None:
            stmt = stmt.where(AthleteProfile.status == filters.status)
        if filters.born_after is not None:
            stmt = stmt.where(AthleteProfile.birth_date > filters.born_after)
        if filters.born_on_or_before is not None:
            stmt = stmt.where(AthleteProfile.birth_date <= filters.born_on_or_before)
        if filters.query:
            nome = func.concat(User.first_name, " ", User.last_name)
            stmt = stmt.where(nome.ilike(f"%{_escapa_like(filters.query)}%", escape="\\"))

        if after is not None:
            stmt = stmt.where(sa.tuple_(Clip.published_at, Clip.id) < sa.tuple_(*after))

        stmt = stmt.order_by(Clip.published_at.desc(), Clip.id.desc()).limit(limit)
        return [FeedRow(clip=c, user=u, profile=p) for c, u, p in self.session.exec(stmt).all()]

    def like_counts(self, clip_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, int]:
        ids = list(clip_ids)
        if not ids:
            return {}
        rows = self.session.exec(
            select(ClipLike.clip_id, func.count())
            .where(ClipLike.clip_id.in_(ids))
            .group_by(ClipLike.clip_id)
        ).all()
        return {clip_id: total for clip_id, total in rows}

    def liked_by(self, user_id: uuid.UUID, clip_ids: Iterable[uuid.UUID]) -> set[uuid.UUID]:
        ids = list(clip_ids)
        if not ids:
            return set()
        return set(
            self.session.exec(
                select(ClipLike.clip_id)
                .where(ClipLike.user_id == user_id)
                .where(ClipLike.clip_id.in_(ids))
            ).all()
        )

    def get_published_clip(self, clip_id: uuid.UUID) -> Optional[Clip]:
        clip = self.session.get(Clip, clip_id)
        if clip is None or clip.status != ClipStatus.PUBLISHED:
            return None
        return clip

    def add_like(self, user_id: uuid.UUID, clip_id: uuid.UUID) -> None:
        # Idempotente: curtir duas vezes não dá erro
        self.session.exec(
            pg_insert(ClipLike)
            .values(user_id=user_id, clip_id=clip_id, created_at=datetime.now(timezone.utc))
            .on_conflict_do_nothing(index_elements=["user_id", "clip_id"])
        )

    def remove_like(self, user_id: uuid.UUID, clip_id: uuid.UUID) -> None:
        self.session.exec(
            sa.delete(ClipLike)
            .where(ClipLike.user_id == user_id)
            .where(ClipLike.clip_id == clip_id)
        )


def _escapa_like(texto: str) -> str:
    """% e _ digitados pelo usuário são texto, não curinga."""
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")