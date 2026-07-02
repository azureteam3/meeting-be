from typing import Any

from fastapi import APIRouter, Query, Request

# services 패키지 경로에서 서비스 객체를 참조
from app.api.routes_communication import communication_service

router = APIRouter(prefix="/callbacks", tags=["acs-callbacks"])


def normalize_event_name(event: dict[str, Any]) -> str:
    raw_type = event.get("type") or event.get("eventType") or ""
    return raw_type.rsplit(".", 1)[-1]


def extract_participants(data: dict[str, Any]) -> list[dict[str, str]]:
    result = []
    for item in data.get("participants", []):
        identifier = item.get("identifier") or item.get("participant") or {}
        raw_id = identifier.get("rawId") or identifier.get("raw_id") or item.get("rawId")
        if raw_id:
            result.append({"raw_id": raw_id})
    return result


@router.post("/acs")
async def acs_callback(
    request: Request,
    session_id: str = Query(...),
) -> dict[str, str]:
    """Azure Communication Services 전화를 제어하는 비동기 이벤트 훅 처리 콜백 API"""
    # 전역 모듈 수준 인스턴스 참조로 수정
    service = communication_service
    events = await request.json()

    if isinstance(events, dict):
        events = [events]

    for event in events:
        data = event.get("data") or {}
        event_name = normalize_event_name(event)

        if event_name == "CallConnected":
            session = service.get_session(session_id)
            session.call_connection_id = data.get("callConnectionId") or session.call_connection_id
            session.server_call_id = data.get("serverCallId") or session.server_call_id
            session.correlation_id = data.get("correlationId") or session.correlation_id
            session.state = "connected"

        elif event_name == "CallDisconnected":
            session = service.get_session(session_id)
            session.state = "disconnected"

        elif event_name == "MediaStreamingStarted":
            session = service.get_session(session_id)
            session.state = "media_streaming_started"

        elif event_name == "ParticipantsUpdated":
            session = service.get_session(session_id)
            session.participants = extract_participants(data)

    return {"status": "ok"}