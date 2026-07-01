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