import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.modules.identity.models import UserRole
from app.modules.opportunities.models import ApplicationStatus, OpportunityMode
from app.modules.profiles.models import Position

_URL = r"^https?://"


class OpportunityCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=1, max_length=5000)
    mode: OpportunityMode
    state: Optional[str] = Field(None, min_length=2, max_length=2)
    city: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=200)
    meeting_url: Optional[str] = Field(None, max_length=500, pattern=_URL)
    # AwareDatetime: data sem fuso é ambígua (o front manda ISO com Z).
    event_at: AwareDatetime
    registration_deadline: AwareDatetime
    min_age: Optional[int] = Field(None, ge=5, le=60)
    max_age: Optional[int] = Field(None, ge=5, le=60)
    positions: List[Position] = []
    max_applications: Optional[int] = Field(None, ge=1, le=10000)


class OpportunityUpdate(BaseModel):
    """PATCH: só os campos enviados mudam (`exclude_unset`). null limpa campo opcional."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: Optional[str] = Field(None, min_length=3, max_length=120)
    description: Optional[str] = Field(None, min_length=1, max_length=5000)
    mode: Optional[OpportunityMode] = None
    state: Optional[str] = Field(None, min_length=2, max_length=2)
    city: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=200)
    meeting_url: Optional[str] = Field(None, max_length=500, pattern=_URL)
    event_at: Optional[AwareDatetime] = None
    registration_deadline: Optional[AwareDatetime] = None
    min_age: Optional[int] = Field(None, ge=5, le=60)
    max_age: Optional[int] = Field(None, ge=5, le=60)
    positions: Optional[List[Position]] = None
    max_applications: Optional[int] = Field(None, ge=1, le=10000)


class Organizer(BaseModel):
    user_id: uuid.UUID
    first_name: str
    last_name: str
    role: UserRole
    avatar_url: Optional[str] = None


class OpportunitySummary(BaseModel):
    id: uuid.UUID
    title: str
    mode: OpportunityMode
    state: Optional[str]
    city: Optional[str]
    event_at: datetime
    registration_deadline: datetime
    min_age: Optional[int]
    max_age: Optional[int]
    positions: List[Position]
    spots_left: Optional[int]
    is_cancelled: bool
    organizer: Organizer


class MyApplication(BaseModel):
    status: ApplicationStatus


class Eligibility(BaseModel):
    eligible: bool
    reason: Optional[str]


class OpportunityDetail(OpportunitySummary):
    description: str
    address: Optional[str]
    meeting_url: Optional[str]
    max_applications: Optional[int]
    is_open: bool
    cancelled_at: Optional[datetime]
    my_application: Optional[MyApplication] = None
    eligibility: Optional[Eligibility] = None


class OpportunityPage(BaseModel):
    items: List[OpportunitySummary]
    next_cursor: Optional[str]


class ApplicationCounts(BaseModel):
    pendente: int = 0
    aprovada: int = 0
    recusada: int = 0


class MyOpportunity(OpportunitySummary):
    is_open: bool
    counts: ApplicationCounts


class Applicant(BaseModel):
    athlete_id: uuid.UUID
    first_name: str
    last_name: str
    avatar_url: Optional[str]
    position: Optional[Position]
    age: Optional[int]
    city: Optional[str]
    state: Optional[str]
    status: ApplicationStatus
    created_at: datetime


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus


class ApplicationOut(BaseModel):
    opportunity_id: uuid.UUID
    athlete_id: uuid.UUID
    status: ApplicationStatus


class MyApplicationItem(BaseModel):
    status: ApplicationStatus
    created_at: datetime
    opportunity: OpportunitySummary
