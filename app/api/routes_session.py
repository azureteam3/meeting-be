from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.schemas.session import SessionStartRequest
from app.services.session_manager import SessionManager
from app.services.speech_transcriber import SpeechTranscriberService
from app.services.acs_audio_bridge import ACSAudioBridge

router = APIRouter(prefix="/sessions", tags=["sessions"])

session_manager = SessionManager()


class AudioChunkRequest(BaseModel):
    audio_base64: str


async def broadcast_to_session(session_id: str, payload: dict):
    dead_sockets = []
    for ws in session_manager.get_websockets(session_id):
        try:
            await ws.send_json(payload)
        except Exception:
            dead_sockets.append(ws)

    for ws in dead_sockets:
        session_manager.remove_websocket(session_id, ws)


@router.post("/start")
def start_session(req: SessionStartRequest):
    result = session_manager.start_session(
        meeting_id=req.meeting_id,
        session_id=req.session_id,
    )

    runtime = session_manager.get_runtime(req.session_id)
    if runtime["transcriber"] is None:
        transcriber = SpeechTranscriberService(
            meeting_id=req.meeting_id,
            session_id=req.session_id,
            on_emit=lambda payload: None
        )
        runtime["bridge"] = ACSAudioBridge(transcriber)
        runtime["transcriber"] = transcriber

        async def async_emit(payload: dict):
            await broadcast_to_session(req.session_id, payload)

        transcriber.on_emit = async_emit
        transcriber.start()

    return result


@router.post("/stop/{session_id}")
def stop_session(session_id: str):
    return session_manager.stop_session(session_id)


@router.get("")
def get_sessions():
    return session_manager.list_sessions()


@router.post("/{session_id}/audio")
def push_audio_chunk(session_id: str, req: AudioChunkRequest):
    runtime = session_manager.get_runtime(session_id)
    if not runtime:
        raise HTTPException(status_code=404, detail="session not found")

    bridge = runtime.get("bridge")
    if not bridge:
        raise HTTPException(status_code=400, detail="audio bridge not initialized")

    bridge.ingest_base64_audio(req.audio_base64)
    return {"message": "audio chunk received", "session_id": session_id}