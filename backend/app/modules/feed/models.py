import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class ClipLike(SQLModel, table=True):
    """Curtida de um usuario em um clipe publicado. Uma por par (usuario, clipe)."""

    __tablename__ = "clip_likes"

    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    # CASCADE: apagar o clipe leva as curtidas junto
    clip_id: uuid.UUID = Field(
        foreign_key="clips.id", primary_key=True, index=True, ondelete="CASCADE"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))