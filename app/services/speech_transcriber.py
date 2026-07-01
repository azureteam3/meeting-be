import asyncio
import azure.cognitiveservices.speech as speechsdk
from azure.cognitiveservices.speech import PropertyId
from app.config import settings
from app.services.transcript_processor import TranscriptProcessor
from app.services.reconnect_manager import ReconnectManager


class SpeechTranscriberService:
    def __init__(self, meeting_id: str, session_id: str, on_emit=None):
        self.meeting_id = meeting_id
        self.session_id = session_id
        self.on_emit = on_emit
        self.processor = TranscriptProcessor()
        self.reconnector = ReconnectManager()
        self._is_running = False

        self.speech_config = speechsdk.SpeechConfig(
            subscription=settings.SPEECH_KEY,
            region=settings.SPEECH_REGION
        )

        auto_detect = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(
            languages=settings.speech_auto_detect_languages
        )

        stream_format = speechsdk.audio.AudioStreamFormat(
            samples_per_second=16000,
            bits_per_sample=16,
            channels=1
        )

        self.push_stream = speechsdk.audio.PushAudioInputStream(stream_format=stream_format)
        self.audio_config = speechsdk.audio.AudioConfig(stream=self.push_stream)

        self.transcriber = speechsdk.transcription.ConversationTranscriber(
            speech_config=self.speech_config,
            audio_config=self.audio_config,
            auto_detect_source_language_config=auto_detect
        )

        self._bind_events()

    def _detect_language(self, result):
        try:
            return result.properties.get(
                PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult
            )
        except Exception:
            return None

    def _speaker_id(self, result):
        return getattr(result, "speaker_id", None) or "unknown"

    def _emit(self, payload):
        if self.on_emit:
            if asyncio.iscoroutinefunction(self.on_emit):
                asyncio.create_task(self.on_emit(payload))
            else:
                self.on_emit(payload)

    def _emit_system(self, event_name: str, detail: str | None = None):
        payload = {
            "type": "system",
            "session_id": self.session_id,
            "meeting_id": self.meeting_id,
            "event": event_name,
            "detail": detail,
        }
        if self.on_emit:
            if asyncio.iscoroutinefunction(self.on_emit):
                asyncio.create_task(self.on_emit(payload))
            else:
                self.on_emit(payload)

    def _handle_transcribing(self, evt):
        result = evt.result
        text = getattr(result, "text", None)
        if not text:
            return

        event = self.processor.process(
            meeting_id=self.meeting_id,
            session_id=self.session_id,
            event_type="interim",
            speaker_id=self._speaker_id(result),
            text=text,
            source_language=self._detect_language(result),
            confidence=None,
            offset_ms=int(result.offset / 10000) if getattr(result, "offset", None) else None,
            duration_ms=int(result.duration / 10000) if getattr(result, "duration", None) else None,
        )
        if event:
            self._emit({
                "type": "transcript",
                "session_id": self.session_id,
                "meeting_id": self.meeting_id,
                "speaker": event.speaker,
                "speaker_id": event.speaker_id,
                "text": event.cleaned_text,
                "translated_text": event.translated_text,
                "language": event.original_language,
                "confidence": event.confidence,
                "is_final": False,
                "status": event.status,
                "offset_ms": event.offset_ms,
                "duration_ms": event.duration_ms,
                "created_at": event.created_at.isoformat(),
            })

    def _handle_transcribed(self, evt):
        result = evt.result
        text = getattr(result, "text", None)
        if not text:
            return

        event = self.processor.process(
            meeting_id=self.meeting_id,
            session_id=self.session_id,
            event_type="final",
            speaker_id=self._speaker_id(result),
            text=text,
            source_language=self._detect_language(result),
            confidence=None,
            offset_ms=int(result.offset / 10000) if getattr(result, "offset", None) else None,
            duration_ms=int(result.duration / 10000) if getattr(result, "duration", None) else None,
        )
        if event:
            self._emit({
                "type": "transcript",
                "session_id": self.session_id,
                "meeting_id": self.meeting_id,
                "speaker": event.speaker,
                "speaker_id": event.speaker_id,
                "text": event.cleaned_text,
                "translated_text": event.translated_text,
                "language": event.original_language,
                "confidence": event.confidence,
                "is_final": True,
                "status": event.status,
                "offset_ms": event.offset_ms,
                "duration_ms": event.duration_ms,
                "created_at": event.created_at.isoformat(),
            })

    def _handle_canceled(self, evt):
        detail = None
        try:
            detail = evt.cancellation_details.error_details
        except Exception:
            detail = "unknown cancel reason"

        self._emit_system("canceled", detail)

        if self.reconnector.can_retry():
            self.reconnector.wait_and_increment()
            self.restart()

    def _handle_session_started(self, evt):
        self.reconnector.reset()
        self._emit_system("session_started")

    def _handle_session_stopped(self, evt):
        self._emit_system("session_stopped")
        if self._is_running and self.reconnector.can_retry():
            self.reconnector.wait_and_increment()
            self.restart()

    def _bind_events(self):
        self.transcriber.transcribing.connect(self._handle_transcribing)
        self.transcriber.transcribed.connect(self._handle_transcribed)
        self.transcriber.canceled.connect(self._handle_canceled)
        self.transcriber.session_started.connect(self._handle_session_started)
        self.transcriber.session_stopped.connect(self._handle_session_stopped)

    def start(self):
        self._is_running = True
        self.transcriber.start_transcribing_async().get()

    def stop(self):
        self._is_running = False
        try:
            self.transcriber.stop_transcribing_async().get()
        finally:
            try:
                self.push_stream.close()
            except Exception:
                pass

    def restart(self):
        try:
            self.transcriber.stop_transcribing_async().get()
        except Exception:
            pass
        self.transcriber.start_transcribing_async().get()

    def push_audio(self, pcm_bytes: bytes):
        self.push_stream.write(pcm_bytes)