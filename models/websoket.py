import base64
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.speech import speech_audio_router

router = APIRouter(tags=["acs-audio"])


@router.websocket("/ws/audio/{session_id}")
async def acs_audio_websocket(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()

    call_connection_id = websocket.headers.get("x-ms-call-connection-id")
    correlation_id = websocket.headers.get("x-ms-call-correlation-id")

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

                if audio_data.get("silent"):
                    continue

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
        await speech_audio_router.close_session(session_id=session_id)