import asyncio
import threading
from typing import Any, Callable, Coroutine

import azure.cognitiveservices.speech as speechsdk
from azure.cognitiveservices.speech import PropertyId

from app.config import settings
from app.services.reconnect_manager import (
    ReconnectManager,
)
from app.services.transcript_processor import (
    TranscriptProcessor,
)


EmitCallback = Callable[
    [dict[str, Any]],
    None | Coroutine[Any, Any, None],
]


class SpeechTranscriberService:
    """
    Azure ConversationTranscriber 기반 실시간 STT 서비스

    입력 형식
    - 16000Hz
    - signed PCM 16-bit
    - mono
    - little-endian
    """

    def __init__(
        self,
        meeting_id: str,
        session_id: str,
        on_emit: EmitCallback | None = None,
        event_loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        self.meeting_id = meeting_id
        self.session_id = session_id
        self.on_emit = on_emit
        self.event_loop = event_loop

        self.processor = TranscriptProcessor()
        self.reconnector = ReconnectManager()

        self._is_running = False
        self._audio_chunk_count = 0
        self._lock = threading.Lock()

        self.speech_config = speechsdk.SpeechConfig(
            subscription=settings.SPEECH_KEY,
            region=settings.SPEECH_REGION,
        )

        auto_detect_languages = (
            settings.speech_auto_detect_languages
        )

        print(
            "[Azure STT] 자동 감지 언어:",
            auto_detect_languages,
        )

        auto_detect = (
            speechsdk.languageconfig
            .AutoDetectSourceLanguageConfig(
                languages=auto_detect_languages
            )
        )

        audio_format = (
            speechsdk.audio.AudioStreamFormat(
                samples_per_second=16000,
                bits_per_sample=16,
                channels=1,
            )
        )

        self.push_stream = (
            speechsdk.audio.PushAudioInputStream(
                stream_format=audio_format
            )
        )

        self.audio_config = (
            speechsdk.audio.AudioConfig(
                stream=self.push_stream
            )
        )

        self.transcriber = (
            speechsdk.transcription
            .ConversationTranscriber(
                speech_config=self.speech_config,
                audio_config=self.audio_config,
                auto_detect_source_language_config=(
                    auto_detect
                ),
            )
        )

        self._bind_events()

    def _detect_language(
        self,
        result: Any,
    ) -> str | None:
        try:
            return result.properties.get(
                PropertyId
                .SpeechServiceConnection_AutoDetectSourceLanguageResult
            )
        except Exception:
            return None

    def _speaker_id(
        self,
        result: Any,
    ) -> str:
        speaker_id = getattr(
            result,
            "speaker_id",
            None,
        )

        return speaker_id or "unknown"

    def _emit(
        self,
        event,
    ) -> None:
        """
        Azure SDK 콜백은 별도 스레드에서 실행될 수 있으므로
        run_coroutine_threadsafe로 메인 이벤트 루프에 전달합니다.
        """

        if not self.on_emit:
            return

        try:
            result = self.on_emit(event)

            if asyncio.iscoroutine(result):
                if (
                    self.event_loop
                    and self.event_loop.is_running()
                ):
                    asyncio.run_coroutine_threadsafe(
                        result,
                        self.event_loop,
                    )
                else:
                    print(
                        "[Azure STT] 실행 중인 이벤트 루프가 없어 "
                        "비동기 emit을 처리하지 못했습니다."
                    )

        except Exception as error:
            print(
                "[Azure STT] emit 실패:",
                error,
            )

    def _emit_system(
        self,
        event_name: str,
        detail: str | None = None,
    ) -> None:
        if not self.on_emit:
            return

        result = self.on_emit({
            "type":"system",
            "session_id":self.session_id,
            "meeting_id":self.meeting_id,
            "event":event_name,
            "detail":detail,
        })

        if asyncio.iscoroutine(result):
            asyncio.run_coroutine_threadsafe(
                result,
                self.event_loop,
            )

    def _handle_transcribing(
        self,
        evt: Any,
    ) -> None:
        """
        중간 인식 결과
        """

        result = evt.result
        text = getattr(
            result,
            "text",
            None,
        )

        if not text:
            return

        detected_language = (
            self._detect_language(result)
        )

        print(
            "[Azure STT] transcribing:",
            f"text={text},",
            f"language={detected_language},",
            f"speaker={self._speaker_id(result)}",
        )

        try:
            event = self.processor.process(
                meeting_id=self.meeting_id,
                session_id=self.session_id,
                event_type="interim",
                speaker_id=self._speaker_id(result),
                text=text,
                source_language=detected_language,
                confidence=None,
                offset_ms=(
                    int(result.offset / 10000)
                    if getattr(
                        result,
                        "offset",
                        None,
                    )
                    else None
                ),
                duration_ms=(
                    int(result.duration / 10000)
                    if getattr(
                        result,
                        "duration",
                        None,
                    )
                    else None
                ),
            )
        except Exception as error:
            print(
                "[Azure STT] interim 처리 실패:",
                error,
            )
            return

        if not event:
            print(
                "[Azure STT] TranscriptProcessor가 "
                "interim 결과를 반환하지 않음:",
                text,
            )
            return

        self._emit(event)

    def _handle_transcribed(
        self,
        evt: Any,
    ) -> None:
        """
        최종 인식 결과
        """

        result = evt.result
        reason = getattr(
            result,
            "reason",
            None,
        )

        text = getattr(
            result,
            "text",
            None,
        )

        print(
            "[Azure STT] transcribed:",
            f"reason={reason},",
            f"text={text!r}",
        )

        if not text:
            return

        detected_language = (
            self._detect_language(result)
        )

        try:
            event = self.processor.process(
                meeting_id=self.meeting_id,
                session_id=self.session_id,
                event_type="final",
                speaker_id=self._speaker_id(result),
                text=text,
                source_language=detected_language,
                confidence=None,
                offset_ms=(
                    int(result.offset / 10000)
                    if getattr(
                        result,
                        "offset",
                        None,
                    )
                    else None
                ),
                duration_ms=(
                    int(result.duration / 10000)
                    if getattr(
                        result,
                        "duration",
                        None,
                    )
                    else None
                ),
            )
        except Exception as error:
            print(
                "[Azure STT] final 처리 실패:",
                error,
            )
            return

        if not event:
            print(
                "[Azure STT] TranscriptProcessor가 "
                "final 결과를 반환하지 않음:",
                text,
            )
            return

        self._emit(event)

    def _handle_canceled(
        self,
        evt: Any,
    ) -> None:
        detail = "unknown cancel reason"
        reason = getattr(
            evt,
            "reason",
            None,
        )

        try:
            cancellation_details = (
                evt.cancellation_details
            )

            detail = (
                cancellation_details.error_details
                or str(cancellation_details.reason)
            )
        except Exception:
            pass

        print(
            "[Azure STT] canceled:",
            f"reason={reason},",
            f"detail={detail}",
        )

        self._emit_system(
            "canceled",
            detail,
        )

        # 현재 PushAudioInputStream을 닫지 않은 상태에서만 재시작
        if (
            self._is_running
            and self.reconnector.can_retry()
        ):
            try:
                self.reconnector.wait_and_increment()
                self.restart()
            except Exception as error:
                print(
                    "[Azure STT] 재시작 실패:",
                    error,
                )

    def _handle_session_started(
        self,
        evt: Any,
    ) -> None:
        print(
            "[Azure STT] session started:",
            self.session_id,
        )

        self.reconnector.reset()
        self._emit_system(
            "session_started"
        )

    def _handle_session_stopped(
        self,
        evt: Any,
    ) -> None:
        print(
            "[Azure STT] session stopped:",
            self.session_id,
        )

        self._emit_system(
            "session_stopped"
        )

        if (
            self._is_running
            and self.reconnector.can_retry()
        ):
            try:
                self.reconnector.wait_and_increment()
                self.restart()
            except Exception as error:
                print(
                    "[Azure STT] 세션 재시작 실패:",
                    error,
                )

    def _bind_events(self) -> None:
        self.transcriber.transcribing.connect(
            self._handle_transcribing
        )

        self.transcriber.transcribed.connect(
            self._handle_transcribed
        )

        self.transcriber.canceled.connect(
            self._handle_canceled
        )

        self.transcriber.session_started.connect(
            self._handle_session_started
        )

        self.transcriber.session_stopped.connect(
            self._handle_session_stopped
        )

    def start(self) -> None:
        if self._is_running:
            return

        print(
            "[Azure STT] start 요청:",
            self.session_id,
        )

        self._is_running = True

        try:
            self.transcriber \
                .start_transcribing_async() \
                .get()

            print(
                "[Azure STT] start 완료:",
                self.session_id,
            )

        except Exception:
            self._is_running = False
            raise

    def stop(self) -> None:
        if not self._is_running:
            return

        print(
            "[Azure STT] stop 요청:",
            self.session_id,
        )

        self._is_running = False

        try:
            self.transcriber \
                .stop_transcribing_async() \
                .get()
        except Exception as error:
            print(
                "[Azure STT] stop 실패:",
                error,
            )

        try:
            self.push_stream.close()
        except Exception as error:
            print(
                "[Azure STT] PushStream 종료 실패:",
                error,
            )

    def restart(self) -> None:
        if not self._is_running:
            return

        print(
            "[Azure STT] restart 요청:",
            self.session_id,
        )

        try:
            self.transcriber \
                .stop_transcribing_async() \
                .get()
        except Exception as error:
            print(
                "[Azure STT] restart stop 실패:",
                error,
            )

        self.transcriber \
            .start_transcribing_async() \
            .get()

    def push_audio(
        self,
        pcm_bytes: bytes,
    ) -> None:
        """
        16kHz PCM16 Mono 데이터 전달
        """

        if not self._is_running:
            print(
                "[Azure STT] 실행 중이 아니어서 "
                "오디오 전달 중단"
            )
            return

        if not pcm_bytes:
            return

        with self._lock:
            self.push_stream.write(
                pcm_bytes
            )

            self._audio_chunk_count += 1

            if self._audio_chunk_count % 20 == 0:
                print(
                    "[Azure STT] PushStream write:",
                    f"chunks={self._audio_chunk_count},",
                    f"bytes={len(pcm_bytes)}",
                )