import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, BigInteger
from sqlalchemy.dialects.postgresql import JSONB, UUID
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


# ── 에이전트(회의 요약·회의록)용 표 3개 (자막팀 transcript_records는 위에서 읽기만 함) ──

class MeetingSummarySnapshot(Base):
    """회의별 '최신 요약' 1개 (요약 요청마다 UPSERT)."""
    __tablename__ = "meeting_summary_snapshot"

    meeting_id = Column(String(100), primary_key=True)
    version = Column(Integer, default=1)
    coverage_to_seq = Column(BigInteger, default=0)
    summary_json = Column(JSONB, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MeetingChatMessage(Base):
    """채팅 이력 - 사용자 질문과 Agent 답변."""
    __tablename__ = "meeting_chat_message"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    meeting_id = Column(String(100), index=True, nullable=False)
    sender_type = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    response_type = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MeetingMinutes(Base):
    """생성된 회의록 - 회의록당 1줄 저장, id(UUID)로 조회."""
    __tablename__ = "meeting_minutes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id = Column(String(100), index=True, nullable=False)
    minutes_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)