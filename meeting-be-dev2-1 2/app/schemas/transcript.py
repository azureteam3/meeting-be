from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class TranscriptIngestRequest(BaseModel):
    meeting_id: str
    session_id: str
    event_type: Literal["interim", "final"]
    speaker: Optional[str] = None
    speaker_id: str = "unknown"
    text: str
    source_language: Optional[str] = None
    confidence: Optional[float] = None
    offset_ms: Optional[int] = None
    duration_ms: Optional[int] = None


class TranscriptEvent(BaseModel):
    segment_id: str
    meeting_id: str
    session_id: str

    event_type: Literal["interim", "final"]

    speaker: Optional[str] = None
    speaker_id: str = "unknown"

    original_text: str
    cleaned_text: str
    translated_text: Optional[str] = None

    original_language: Optional[str] = None
    target_language: str = "ko"

    confidence: Optional[float] = None
    is_reliable: bool = True
    needs_review: bool = False

    status: Literal[
        "recognizing",
        "recognized",
        "translated",
        "bypass_ko",
        "failed",
        "final",
    ] = "recognized"

    offset_ms: Optional[int] = None
    duration_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)