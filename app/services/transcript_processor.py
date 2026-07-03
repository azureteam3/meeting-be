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

        elif event_type == "final":
            if normalized_lang == settings.TARGET_LANGUAGE:
                translated_text = cleaned
                is_translated = False
                status = "bypass_ko"
            elif normalized_lang in settings.translator_source_languages:
                try:
                    translated_text = self.translator.translate_to_korean(
                        text=cleaned,
                        source_language=normalized_lang
                    )
                    is_translated = True
                    status = "translated"
                except Exception as e:
                    translated_text = cleaned
                    translation_error = str(e)
                    is_translated = False
                    status = "translated_fallback"
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

        try:
            self.repository.save_event(event)
        except Exception as e:
            print("[Transcript DB Save Failed]", e)
            
            # ✔ 1회 retry
            try:
                self.repository.save_event(event)
            except Exception as e2:
                print("[Transcript DB FINAL FAIL]", e2)
                # pipeline 절대 중단 안 함

        if event_type == "final":
            self.foundry_router.route(event)

        return event