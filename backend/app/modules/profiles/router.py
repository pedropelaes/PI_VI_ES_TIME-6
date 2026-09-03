"""
HTTP do modulo de perfis: rota, validacao e serializacao. Sem regra de negocio.
Erros sobem como excecao de dominio e sao traduzidos pelo handler unico do main.py.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_user
from app.modules.identity.models import User
from app.modules.profiles.repository import SqlAthleteProfileRepository
from app.modules.profiles.schemas import AthleteProfileResponse
from app.modules.profiles.service import AthleteProfileView, ProfilesService

router = APIRouter(prefix="/profiles", tags=["profiles"])


def get_service(session: Session = Depends(get_session)) -> ProfilesService:
    return ProfilesService(SqlAthleteProfileRepository(session))


def _to_response(view: AthleteProfileView) -> AthleteProfileResponse:
    return AthleteProfileResponse(
        user_id=view.user_id,
        first_name=view.first_name,
        last_name=view.last_name,
        position=view.position,
        status=view.status,
        age=view.age,
        height_cm=view.height_cm,
        dominant_foot=view.dominant_foot,
        city=view.city,
        state=view.state,
        current_club=view.current_club,
        bio=view.bio,
        avatar_url=view.avatar_path,
        clips_count=view.clips_count,
    )


@router.get("/athletes/{user_id}", response_model=AthleteProfileResponse)
def get_athlete_profile(
    user_id: uuid.UUID,
    service: ProfilesService = Depends(get_service),
    current_user: User = Depends(get_current_user),
):
    """Perfil de um atleta. Exige autenticacao (decisao P2 da spec)."""
    return _to_response(service.get_athlete_profile(user_id))
