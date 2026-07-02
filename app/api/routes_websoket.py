import base64
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# STT / 음성 AI 연동 서비스 가상 라우터 임포트 구조 유지
from app.services.speech import speech_audio_router

router = APIRouter(tags=["acs-audio"])


@router.websocket("/ws/audio/{session_id}")
async def acs_audio_websocket(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()

    # ACS 스트리밍 연결 시 추적성 개선을 위한 헤더 추출
    call_connection_id = websocket.headers.get("x-ms-call-connection-id")
    correlation_id = websocket.headers.get("x-ms-call-correlation-id")

    # 오디오 세션 컨텍스트 오픈
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

                # 묵음 구간 패킷 필터링링
                if audio_data.get("silent"):
                    continue

                # 오디오 스트리밍 데이터를 바이너리 PCM 스트림으로 디코딩
                pcm = base64.b64decode(audio_data["data"])

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
        # 연결 종료 시 리소스 정리 및 닫기 보장
        await speech_audio_router.close_session(session_id=session_id)