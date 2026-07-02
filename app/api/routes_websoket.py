import base64
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# 실시간 STT 엔진 및 음성 서비스 가상 처리 라우터 연동
from app.services.speech import speech_audio_router

router = APIRouter(tags=["acs-audio"])


@router.websocket("/ws/audio/{session_id}")
async def acs_audio_websocket(websocket: WebSocket, session_id: str) -> None:
    """통화 상태에서 넘어오는 실시간 PCM 스트림 오디오 이중 송수신 웹소켓 게이트웨이"""
    await websocket.accept()

    call_connection_id = websocket.headers.get("x-ms-call-connection-id")
    correlation_id = websocket.headers.get("x-ms-call-correlation-id")

    # 세션 열기 트리거
    await speech_audio_router.open_session(
        session_id=session_id,
        call_connection_id=call_connection_id,
        correlation_id=correlation_id,
    )

    try:
        while True:
            message = await websocket.receive_text()
            packet = json.loads(message)
            kind = packet.get("kind")

            if kind == "AudioMetadata":
                await speech_audio_router.set_metadata(
                    session_id=session_id,
                    metadata=packet.get("audioMetadata") or {},
                )

            elif kind == "AudioData":
                audio_data = packet.get("audioData") or {}

                # 묵음 필터링 처리로 대역폭 절약
                if audio_data.get("silent"):
                    continue

                pcm = base64.b64decode(audio_data["data"])

                # AI 오디오 파이프라인(STT/Speech 엔진)으로 직진 처리
                await speech_audio_router.push_pcm(
                    session_id=session_id,
                    pcm=pcm,
                    participant_raw_id=audio_data.get("participantRawID"),
                    timestamp=audio_data.get("timestamp"),
                )

            elif kind == "DtmfData":
                await speech_audio_router.push_dtmf(
                    session_id=session_id,
                    data=packet.get("dtmfData") or {},
                )

    except WebSocketDisconnect:
        pass

    finally:
        # 종료 시 오디오 스트리밍 세션 정리 보장
        await speech_audio_router.close_session(session_id=session_id)