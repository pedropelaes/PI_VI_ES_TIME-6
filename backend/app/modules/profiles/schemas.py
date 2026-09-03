"""DTOs de entrada e saida do modulo de perfis."""
import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from app.modules.profiles.models import AthleteStatus, DominantFoot, Position


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


class AthleteProfileUpdate(BaseModel):
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
