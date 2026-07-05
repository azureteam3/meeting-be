import uuid
from app.schemas.transcript import TranscriptEvent
from app.utils.text_cleaner import clean_transcript_text
from app.utils.language_map import normalize_language
from app.services.translator_service import TranslatorService
from app.repositories.transcript_repository import TranscriptRepository
from app.services.foundry_router import FoundryRouter
from app.config import settings


class TranscriptProcessor:
    def __init__(self):
        self.translator = TranslatorService()
        self.repository = TranscriptRepository()
        self.foundry_router = FoundryRouter()

    def _make_segment_id(self) -> str:
        return f"seg-{uuid.uuid4().hex[:12]}"

    def process(
        self,
        meeting_id: str,
        session_id: str,
        event_type: str,
        speaker_id: str,
        text: str,
        source_language: str | None = None,
        confidence: float | None = None,
        offset_ms: int | None = None,
        duration_ms: int | None = None,
        speaker: str | None = None,
    ) -> TranscriptEvent | None:
        if not text or len(text.strip()) < settings.MIN_TEXT_LENGTH:
            return None

        cleaned = clean_transcript_text(text)
        if len(cleaned) < settings.MIN_TEXT_LENGTH:
            return None

        normalized_lang = normalize_language(source_language)

        is_reliable = confidence is None or confidence >= settings.MIN_CONFIDENCE
        needs_review = not is_reliable

        translated_text = None
        translation_error = None
        is_translated = False
        status = "recognized"

        if event_type == "interim":
            status = "recognizing"
            translated_text = None

        elif event_type == "final":
            status = "final"
            translated_text = None   # ❗ 여기 핵심
 
        else:
            translated_text = cleaned
            is_translated = False
            status = "recognized"

        event = TranscriptEvent(
            segment_id=self._make_segment_id(),
            meeting_id=meeting_id,
            session_id=session_id,
            event_type=event_type,
            speaker=speaker,
            speaker_id=speaker_id or "unknown",
            original_text=text,
            cleaned_text=cleaned,
            translated_text=translated_text,
            original_language=normalized_lang,
            target_language=settings.TARGET_LANGUAGE,
            confidence=confidence,
            is_reliable=is_reliable,
            needs_review=needs_review,
            status=status,
            offset_ms=offset_ms,
            duration_ms=duration_ms,
            translation_error=translation_error,
            is_final_for_summary=(event_type == "final"),
        )

        event._meta = {
            "raw_original": text,
            "cleaned": cleaned,
            "normalized_language": normalized_lang,
            "is_translated": is_translated,
            "translation_error": translation_error,
            "meeting_id": meeting_id,
            "session_id": session_id,
            "event_type": event_type,
        }     

        return event