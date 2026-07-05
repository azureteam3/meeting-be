import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.session_manager import session_manager
from app.services.speech import speech_audio_router


router = APIRouter(tags=["stream"])


@router.websocket("/ws/{session_id}")
async def websocket_stream(
    websocket: WebSocket,
    session_id: str,
) -> None:
    """
    프론트 WebSocket 연결 처리

    수신 데이터
    - text: join, start_transcription, stop_transcription 등 JSON
    - bytes: 16kHz / PCM16 / Mono 마이크 오디오
    """

    await websocket.accept()

    runtime = session_manager.get_runtime(session_id)

    if not runtime:
        await websocket.send_json({
            "type": "error",
            "payload": {
                "message": "session not found",
            },
        })

        await websocket.close(code=1008)
        return

    session_manager.add_websocket(
        session_id,
        websocket,
    )

    # WebSocket 연결 시 Azure Speech 세션 생성
    try:
        await speech_audio_router.open_session(
            session_id=session_id,
            call_connection_id=None,
            correlation_id=None,
        )
    except Exception as error:
        print(
            "[WebSocket] Speech 세션 생성 실패:",
            f"session={session_id},",
            f"error={error}",
        )

        session_manager.remove_websocket(
            session_id,
            websocket,
        )

    audio_chunk_count = 0

    try:
        while True:
            message: dict[str, Any] = (
                await websocket.receive()
            )

            message_type = message.get("type")

            # Starlette가 전달한 WebSocket disconnect 이벤트
            if message_type == "websocket.disconnect":
                break

            # 프론트에서 전달한 PCM16 오디오 바이너리
            audio_bytes = message.get("bytes")

            if audio_bytes is not None:
                if not isinstance(audio_bytes, bytes):
                    print(
                        "[WebSocket] 잘못된 바이너리 형식:",
                        type(audio_bytes),
                    )
                    continue

                audio_chunk_count += 1

                if audio_chunk_count % 20 == 0:
                    print(
                        "[WebSocket] 오디오 수신:",
                        f"session={session_id},",
                        f"chunks={audio_chunk_count},",
                        f"bytes={len(audio_bytes)}",
                    )

                await speech_audio_router.push_pcm(
                    session_id=session_id,
                    pcm=audio_bytes,
                    participant_raw_id=None,
                    timestamp=None,
                )

                continue

            # 프론트 JSON 메시지
            text_data = message.get("text")

            if text_data is None:
                continue

            try:
                client_message = json.loads(text_data)
            except json.JSONDecodeError as error:
                print(
                    "[WebSocket] JSON 파싱 실패:",
                    text_data,
                    error,
                )

                await websocket.send_json({
                    "type": "error",
                    "payload": {
                        "message": "invalid JSON message",
                    },
                })

                continue

            await handle_client_message(
                websocket=websocket,
                session_id=session_id,
                message=client_message,
            )

    except WebSocketDisconnect:
        print(
            "[WebSocket] 연결 종료:",
            session_id,
        )

    except Exception as error:
        print(
            "[WebSocket] 처리 오류:",
            f"session={session_id},",
            f"error={error}",
        )

        try:
            await websocket.send_json({
                "type": "error",
                "payload": {
                    "message": "WebSocket 처리 중 오류가 발생했습니다.",
                    "detail": str(error),
                },
            })
        except Exception:
            pass

    finally:
        session_manager.remove_websocket(
            session_id,
            websocket,
        )

        # 같은 세션에 연결된 클라이언트가 없다면 STT 정리
        remaining_websockets = (
            session_manager.get_websockets(session_id)
        )

        if not remaining_websockets:
            await speech_audio_router.close_session(
                session_id
            )

        try:
            await websocket.close()
        except Exception:
            pass


async def handle_client_message(
    websocket: WebSocket,
    session_id: str,
    message: dict[str, Any],
) -> None:
    """
    프론트에서 보내는 JSON 메시지 처리
    """

    message_type = message.get("type")
    payload = message.get("payload")

    if not isinstance(payload, dict):
        payload = {}

    print(
        "[WebSocket] JSON 수신:",
        f"session={session_id},",
        f"type={message_type}",
    )

    if message_type == "join":
        username = payload.get("username")
        language = payload.get("language", "ko")

        await speech_audio_router.set_metadata(
            session_id,
            {
                "username": username,
                "language": language,
            },
        )

        await websocket.send_json({
            "type": "joined",
            "payload": {
                "session_id": session_id,
                "username": username,
                "language": language,
            },
        })

        return

    if message_type == "start_transcription":
        await speech_audio_router.set_metadata(
            session_id,
            payload,
        )

        await websocket.send_json({
            "type": "transcription_started",
            "payload": {
                "sampleRate": payload.get(
                    "sampleRate",
                    16000,
                ),
                "format": payload.get(
                    "format",
                    "pcm_s16le",
                ),
                "channels": payload.get(
                    "channels",
                    1,
                ),
                "language": payload.get(
                    "language",
                    "ko",
                ),
            },
        })

        return

    if message_type == "stop_transcription":
        # 여기서 close_session()을 호출하면
        # 마이크를 다시 켰을 때 기존 PushAudioInputStream을 사용할 수 없음
        await websocket.send_json({
            "type": "transcription_stopped",
        })

        return

    if message_type == "toggle_mic":
        print(
            "[WebSocket] 마이크 상태:",
            payload.get("on"),
        )
        return

    if message_type == "toggle_video":
        print(
            "[WebSocket] 카메라 상태:",
            payload.get("on"),
        )
        return

    if message_type == "leave":
        print(
            "[WebSocket] 사용자 퇴장 요청:",
            session_id,
        )
        return

    print(
        "[WebSocket] 알 수 없는 메시지:",
        message,
    )

    async def push_transcript(websocket, event):
        await websocket.send_json({
            "type": "transcript",
            "payload": {
                "id": event.segment_id,
                "original": event.cleaned_text,
                "translated": event.translated_text,
                "is_final": event.event_type == "final"
            }
        })
    
    async def push_translation_update(websocket, segment_id, ko):
        await websocket.send_json({
            "type": "translation_update",
            "payload": {
                "id": segment_id,
                "translated": ko
            }
        })