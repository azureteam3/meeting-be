import asyncio
from typing import Any

from app.services.session_manager import session_manager
from app.services.speech_transcriber import (
    SpeechTranscriberService,
)


class SpeechAudioRouter:
    """
    WebSocket 마이크 오디오와 Azure Speech 서비스를 연결합니다.
    """

    def __init__(self) -> None:
        self._active_transcribers: dict[
            str,
            SpeechTranscriberService,
        ] = {}

        self._metadata: dict[
            str,
            dict[str, Any],
        ] = {}

        self._pcm_chunk_counts: dict[str, int] = {}

    async def open_session(
        self,
        session_id: str,
        call_connection_id: str | None,
        correlation_id: str | None,
        preferred_language: str | None = None,
    ) -> None:
        """
        세션별 Azure Speech Transcriber 생성
        """

        existing = self._active_transcribers.get(
            session_id
        )

        if existing:
            print(
                "[SpeechRouter] 기존 STT 세션 사용:",
                session_id,
            )
            return

        runtime = session_manager.get_runtime(
            session_id
        )

        meeting_id = (
            runtime["meeting_id"]
            if runtime
            and runtime.get("meeting_id")
            else session_id
        )

        event_loop = asyncio.get_running_loop()

        async def handle_emit(
            event,
        ) -> None:
            from app.services.transcript_service import transcript_service

            # system 이벤트는 로그만 출력
            if isinstance(event, dict):
                print("[SpeechRouter] Azure 상태:", event)
                return

            print(
                "[SpeechRouter] 자막:",
                event.cleaned_text,
                "| final:",
                event.event_type == "final",
            )

            await transcript_service.handle_event(event)

        transcriber = SpeechTranscriberService(
            meeting_id=meeting_id,
            session_id=session_id,
            on_emit=handle_emit,
            event_loop=event_loop,
            preferred_language=preferred_language,
        )

        # 딕셔너리에 먼저 저장해야 시작 직후
        # 오디오가 들어와도 조회할 수 있음
        self._active_transcribers[
            session_id
        ] = transcriber

        self._pcm_chunk_counts[
            session_id
        ] = 0

        try:
            transcriber.start()
        except Exception:
            self._active_transcribers.pop(
                session_id,
                None,
            )
            self._pcm_chunk_counts.pop(
                session_id,
                None,
            )
            raise

        if runtime:
            session_manager.set_transcriber(
                session_id,
                transcriber,
            )

        print(
            "[SpeechRouter] STT 세션 시작:",
            f"session={session_id},",
            f"meeting={meeting_id}",
        )

    async def set_metadata(
        self,
        session_id: str,
        metadata: dict[str, Any],
    ) -> None:
        """
        언어, 샘플레이트 등 프론트 메타데이터 저장
        """

        current = self._metadata.setdefault(
            session_id,
            {},
        )

        current.update(metadata)

        print(
            "[SpeechRouter] 메타데이터:",
            f"session={session_id},",
            current,
        )

    async def push_pcm(
        self,
        session_id: str,
        pcm: bytes,
        participant_raw_id: str | None,
        timestamp: str | None,
    ) -> None:
        """
        프론트에서 받은 PCM16 데이터를 Azure PushStream에 전달
        """

        if not pcm:
            return

        transcriber = self._active_transcribers.get(
            session_id
        )

        if not transcriber:
            print(
                "[SpeechRouter] 활성 transcriber 없음:",
                session_id,
            )
            return

        count = (
            self._pcm_chunk_counts.get(
                session_id,
                0,
            )
            + 1
        )

        self._pcm_chunk_counts[
            session_id
        ] = count

        if count % 20 == 0:
            print(
                "[SpeechRouter] PCM 전달:",
                f"session={session_id},",
                f"chunks={count},",
                f"bytes={len(pcm)}",
            )

        try:
            transcriber.push_audio(pcm)
        except Exception as error:
            print(
                "[SpeechRouter] PCM 전달 실패:",
                f"session={session_id},",
                f"error={error}",
            )

    async def push_dtmf(
        self,
        session_id: str,
        data: dict[str, Any],
    ) -> None:
        print(
            "[SpeechRouter] DTMF 수신:",
            f"session={session_id},",
            f"tone={data.get('tone')}",
        )

    async def close_session(
        self,
        session_id: str,
    ) -> None:
        """
        WebSocket 클라이언트가 모두 종료되면 STT 정리
        """

        print(
            "[SpeechRouter] STT 세션 종료:",
            session_id,
        )

        transcriber = (
            self._active_transcribers.pop(
                session_id,
                None,
            )
        )

        self._metadata.pop(
            session_id,
            None,
        )

        self._pcm_chunk_counts.pop(
            session_id,
            None,
        )

        if transcriber:
            try:
                transcriber.stop()
            except Exception as error:
                print(
                    "[SpeechRouter] STT 종료 실패:",
                    error,
                )


speech_audio_router = SpeechAudioRouter()
