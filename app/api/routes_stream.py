from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.api.routes_session import session_manager

router = APIRouter(tags=["stream"])


@router.websocket("/ws/{session_id}")
async def websocket_stream(websocket: WebSocket, session_id: str):
    await websocket.accept()

    runtime = session_manager.get_runtime(session_id)
    if not runtime:
        await websocket.send_json({
            "type": "system",
            "event": "error",
            "detail": "session not found",
            "session_id": session_id,
        })
        await websocket.close()
        return

    session_manager.add_websocket(session_id, websocket)

    await websocket.send_json({
        "type": "system",
        "event": "connected",
        "session_id": session_id,
    })

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        session_manager.remove_websocket(session_id, websocket)
    except Exception:
        session_manager.remove_websocket(session_id, websocket)
        await websocket.close()