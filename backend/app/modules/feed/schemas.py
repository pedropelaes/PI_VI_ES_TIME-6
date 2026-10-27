import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.modules.profiles.models import AthleteStatus, Position


class FeedAthlete(BaseModel):
    user_id: uuid.UUID
    first_name: str
    last_name: str
    avatar_url: Optional[str]
    position: Optional[Position]
    age: Optional[int]
    city: Optional[str]
    state: Optional[str]
    status: AthleteStatus


class FeedItem(BaseModel):
    id: uuid.UUID
    file_url: str
    duration_seconds: float
    published_at: datetime
    like_count: int
    liked_by_me: bool
    athlete: FeedAthlete


class FeedPage(BaseModel):
    items: List[FeedItem]
    next_cursor: Optional[str]


class LikeState(BaseModel):
    clip_id: uuid.UUID
    like_count: int
    liked_by_me: bool