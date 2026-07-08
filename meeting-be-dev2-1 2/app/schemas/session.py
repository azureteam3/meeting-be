from pydantic import BaseModel
from datetime import datetime

class SessionStartRequest(BaseModel):
    meeting_id: str
    session_id: str

class SessionResponse(BaseModel):
    message: str
    meeting_id: str | None = None
    session_id: str
    status: str | None = None
    created_at: datetime | None = None

class TokenResponse(BaseModel):
    identity: str
    token: str
    expires_on: datetime

class ParticipantRequest(BaseModel):
    user_id: str
    user_name: str | None = None

class ParticipantResponse(BaseModel):
    message: str
    user_id: str
    success: bool = True

class SessionInfo(BaseModel):
    meeting_id: str
    session_id: str
    status: str
    participant_count: int
    created_at: datetime

class ParticipantInfo(BaseModel):
    user_id: str
    user_name: str | None = None

class ParticipantListResponse(BaseModel):
    participants: list[ParticipantInfo]