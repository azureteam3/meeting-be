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
        status = "recognized"

        if event_type == "interim":
            status = "recognizing"

        elif event_type == "final":
            if normalized_lang == settings.TARGET_LANGUAGE:
                translated_text = cleaned
                status = "bypass_ko"
            elif normalized_lang in settings.translator_source_languages:
                try:
                    translated_text = self.translator.translate_to_korean(
                        text=cleaned,
                        source_language=normalized_lang
                    )
                    status = "translated"
                except Exception:
                    translated_text = None
                    status = "failed"
            else:
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
        )

        self.repository.save_event(event)

        if event_type == "final":
            self.foundry_router.route(event)

        return event