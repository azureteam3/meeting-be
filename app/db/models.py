from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float
from datetime import datetime
from app.db.postgres import Base


class MeetingSession(Base):
    __tablename__ = "meeting_sessions"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(String(100), nullable=False, index=True)
    session_id = Column(String(100), nullable=False, unique=True, index=True)
    status = Column(String(30), nullable=False, default="started")
    created_at = Column(DateTime, default=datetime.utcnow)


class TranscriptRecord(Base):
    __tablename__ = "transcript_records"

    id = Column(Integer, primary_key=True, index=True)
    segment_id = Column(String(50), unique=True, index=True, nullable=False)

    meeting_id = Column(String(100), nullable=False, index=True)
    session_id = Column(String(100), nullable=False, index=True)

    event_type = Column(String(20), nullable=False)

    speaker = Column(String(100), nullable=True)
    speaker_id = Column(String(100), nullable=False)

    original_text = Column(Text, nullable=False)
    cleaned_text = Column(Text, nullable=False)
    translated_text = Column(Text, nullable=True)

    original_language = Column(String(20), nullable=True)
    target_language = Column(String(20), nullable=False, default="ko")

    confidence = Column(Float, nullable=True)
    is_reliable = Column(Boolean, default=True)
    needs_review = Column(Boolean, default=False)

    status = Column(String(30), nullable=False, default="recognized")

    offset_ms = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)