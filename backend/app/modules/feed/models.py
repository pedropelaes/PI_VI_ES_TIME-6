import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


class ClipLike(SQLModel, table=True):
    """Curtida de um usuario em um clipe publicado. Uma por par (usuario, clipe)."""

    __tablename__ = "clip_likes"

    # ondelete=CASCADE: apagar o usuario leva as curtidas dele junto.
    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True, ondelete="CASCADE")
    # ondelete=CASCADE: apagar o clipe (usuario ou retencao) leva as curtidas junto.
    clip_id: uuid.UUID = Field(
        foreign_key="clips.id", primary_key=True, index=True, ondelete="CASCADE"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )