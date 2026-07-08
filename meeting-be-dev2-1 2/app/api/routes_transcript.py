from fastapi import APIRouter, Query
from app.schemas.transcript import TranscriptIngestRequest
from app.services.transcript_processor import TranscriptProcessor
from app.repositories.transcript_repository import TranscriptRepository
from app.services.transcript_service import transcript_service

router = APIRouter(prefix="/transcripts", tags=["transcripts"])

processor = TranscriptProcessor()
repository = TranscriptRepository()


@router.post("/ingest")
async def ingest_transcript(req: TranscriptIngestRequest):
    event = processor.process(
        meeting_id=req.meeting_id,
        session_id=req.session_id,
        event_type=req.event_type,
        speaker=req.speaker,
        speaker_id=req.speaker_id,
        text=req.text,
        source_language=req.source_language,
        confidence=req.confidence,
        offset_ms=req.offset_ms,
        duration_ms=req.duration_ms,
    )
    if not event:
        return {"message": "ignored"}

    await transcript_service.handle_event(event)

    return event.model_dump()

@router.get("")
def list_transcripts(session_id: str | None = Query(default=None)):
    return repository.list_events(session_id=session_id)