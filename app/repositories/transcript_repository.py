from app.db.postgres import SessionLocal
from app.db.models import TranscriptRecord
from app.schemas.transcript import TranscriptEvent


class TranscriptRepository:
    def save_event(self, event: TranscriptEvent):
        db = SessionLocal()
        try:
            row = TranscriptRecord(
                segment_id=event.segment_id,
                meeting_id=event.meeting_id,
                session_id=event.session_id,
                event_type=event.event_type,
                speaker=event.speaker,
                speaker_id=event.speaker_id,
                original_text=event.original_text,
                cleaned_text=event.cleaned_text,
                translated_text=event.translated_text,
                original_language=event.original_language,
                target_language=event.target_language,
                confidence=event.confidence,
                is_reliable=event.is_reliable,
                needs_review=event.needs_review,
                status=event.status,
                offset_ms=event.offset_ms,
                duration_ms=event.duration_ms,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return row
        finally:
            db.close()

    def list_events(self, session_id: str | None = None):
        db = SessionLocal()
        try:
            query = db.query(TranscriptRecord)
            if session_id:
                query = query.filter(TranscriptRecord.session_id == session_id)

            rows = query.order_by(TranscriptRecord.created_at.desc()).all()

            return [
                {
                    "segment_id": row.segment_id,
                    "meeting_id": row.meeting_id,
                    "session_id": row.session_id,
                    "event_type": row.event_type,
                    "speaker": row.speaker,
                    "speaker_id": row.speaker_id,
                    "original_text": row.original_text,
                    "cleaned_text": row.cleaned_text,
                    "translated_text": row.translated_text,
                    "original_language": row.original_language,
                    "target_language": row.target_language,
                    "confidence": row.confidence,
                    "is_reliable": row.is_reliable,
                    "needs_review": row.needs_review,
                    "status": row.status,
                    "offset_ms": row.offset_ms,
                    "duration_ms": row.duration_ms,
                    "created_at": row.created_at,
                }
                for row in rows
            ]
        finally:
            db.close()