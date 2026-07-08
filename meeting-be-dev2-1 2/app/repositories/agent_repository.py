"""
app/repositories/agent_repository.py - 에이전트(회의 요약·회의록)용 DB 함수 모음.

- 자막 조회: 자막팀 표(TranscriptRecord = transcript_records)를 meeting_id로 '읽기만' 한다.
- 요약/회의록 저장: 우리 표(MeetingSummarySnapshot, MeetingMinutes)에 한다.

FastAPI 라우트가 get_db로 넘겨준 db(세션)를 인자로 받아 쓴다.
"""

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.models import MeetingMinutes, MeetingSummarySnapshot, TranscriptRecord


def get_summary_snapshot(db: Session, meeting_id):
    """이 회의의 '현재(최신) 요약' 1개 = 워터마크가 가장 큰 행. 없으면 None.

    (append-only라 행이 여러 개 쌓임 → 커버리지 내림차순, 같으면 나중 행이 현재본)
    """
    return (
        db.query(MeetingSummarySnapshot)
        .filter_by(meeting_id=meeting_id)
        .order_by(
            MeetingSummarySnapshot.coverage_to_seq.desc(),
            MeetingSummarySnapshot.id.desc(),
        )
        .first()
    )


def get_transcripts(db: Session, meeting_id, speaker_id=None, after_id=None):
    """이 회의 자막을 회의 내 순서(offset_ms → id)로 꺼낸다.

    - after_id: 이 자막 id '초과'인 것만 (증분 요약용 새 자막. 생략하면 전체)
    """
    query = db.query(TranscriptRecord).filter_by(meeting_id=meeting_id)
    if speaker_id is not None:
        query = query.filter_by(speaker_id=speaker_id)
    if after_id is not None:
        query = query.filter(TranscriptRecord.id > after_id)
    return query.order_by(TranscriptRecord.offset_ms, TranscriptRecord.id).all()


def get_last_transcript_id(db: Session, meeting_id):
    """이 회의의 마지막(최대) 자막 id. 자막이 없으면 None. (요약 신선도 검사용)"""
    return (
        db.query(func.max(TranscriptRecord.id))
        .filter_by(meeting_id=meeting_id)
        .scalar()
    )


def search_transcripts(db: Session, meeting_id, keyword=None):
    """이 회의 자막을 키워드(정제본/원문 포함)로 검색."""
    query = db.query(TranscriptRecord).filter_by(meeting_id=meeting_id)
    if keyword is not None:
        like = f"%{keyword}%"
        query = query.filter(
            or_(TranscriptRecord.cleaned_text.ilike(like), TranscriptRecord.original_text.ilike(like))
        )
    return query.order_by(TranscriptRecord.offset_ms, TranscriptRecord.id).all()


def get_participants(db: Session, meeting_id):
    """이 회의 참가자 = 자막 화자에서 중복 없이. (speaker_id, speaker) 목록."""
    return (
        db.query(TranscriptRecord.speaker_id, TranscriptRecord.speaker)
        .filter_by(meeting_id=meeting_id)
        .distinct()
        .all()
    )


def save_summary_snapshot(db: Session, meeting_id, summary_json, coverage_to_seq):
    """요약 스냅샷을 '새 행'으로 저장한다 (append-only — 어떤 행도 수정하지 않음).

    덮어쓰기가 없어서 동시 갱신이 겹쳐도 서로를 지우지 못하고(레이스 구조적 제거),
    요약 변화 이력이 그대로 남는다. version은 참고용(이전+1).
    """
    prev = get_summary_snapshot(db, meeting_id)
    snap = MeetingSummarySnapshot(
        meeting_id=meeting_id,
        version=(prev.version + 1) if prev else 1,
        coverage_to_seq=coverage_to_seq,
        summary_json=summary_json,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap


def save_minutes(db: Session, meeting_id, minutes_json):
    """회의록을 새 행으로 저장(이력 보관). 저장된 행(id 포함) 반환."""
    row = MeetingMinutes(meeting_id=meeting_id, minutes_json=minutes_json)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_minutes(db: Session, minutes_id):
    """회의록 id로 한 건 조회. 없으면 None."""
    return db.query(MeetingMinutes).filter_by(id=minutes_id).first()


def get_latest_minutes(db: Session, meeting_id):
    """이 회의의 가장 최근 회의록 1건. 없으면 None."""
    return (
        db.query(MeetingMinutes)
        .filter_by(meeting_id=meeting_id)
        .order_by(MeetingMinutes.created_at.desc())
        .first()
    )
