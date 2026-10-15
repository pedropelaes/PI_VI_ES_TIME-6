from pydantic import BaseModel, Field


class ConfirmPlayerRequest(BaseModel):
    candidate_signature: str
    start_ts: int = 0
    end_ts: int = 0


class GoogleDriveImportRequest(BaseModel):
    file_id: str
    google_access_token: str
    target_number: int = Field(..., ge=1, le=999)
    start_ts: int = 0
    end_ts: int = 0
