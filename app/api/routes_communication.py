from datetime import datetime
from fastapi import APIRouter, HTTPException

from app.schemas.session import ParticipantRequest, ParticipantResponse, SessionResponse, TokenResponse
from app.services.communication_service import ACSCommunicationService
from app.config import settings

router = APIRouter(prefix="/communication", tags=["Communication"])

# 설정 정보를 기반으로 서비스 싱글톤 인스턴스 초기화 구성
communication_service = ACSCommunicationService(
    connection_string=settings.ACS_CONNECTION_STRING,
    callback_url=settings.ACS_CALLBACK_URL,
    audio_ws_url_template=settings.AUDIO_WS_URL_TEMPLATE,
)


@router.post(
    "/sessions",
    response_model=SessionResponse,
)
def create_session():
    session = communication_service.create_session()

    return SessionResponse(
        message="Session created successfully",
        meeting_id=None,
        session_id=session.id,
        status=session.state,
        created_at=datetime.utcnow()
    )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
)
def get_session(session_id: str):
    try:
        session = communication_service.get_session(session_id)

        return SessionResponse(
            message="Session found",
            meeting_id=None,
            session_id=session.id,
            status=session.state,
        )

    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    hang_up: bool = False,
):
    try:
        communication_service.delete_session(
            session_id,
            hang_up=hang_up,
        )

        return {
            "message": "Session deleted successfully"
        }

    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Session not found",
        )


@router.post(
    "/token",
    response_model=TokenResponse,
)
def issue_token():
    token = communication_service.issue_token()

    return TokenResponse(
        identity=token["identity"],
        token=token["token"],
        expires_on=token["expires_on"],
    )


@router.post(
    "/sessions/{session_id}/participants",
    response_model=ParticipantResponse,
)
def add_participant(
    session_id: str,
    request: ParticipantRequest,
):
    try:
        communication_service.add_participant(
            session_id=session_id,
            participant_raw_id=request.user_id,
            participant_kind="acs_user"
        )

        return ParticipantResponse(
            message="Participant added successfully",
            user_id=request.user_id,
            success=True,
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.delete(
    "/sessions/{session_id}/participants/{user_id}",
    response_model=ParticipantResponse,
)
def remove_participant(
    session_id: str,
    user_id: str,
):
    try:
        communication_service.remove_participant(
            session_id=session_id,
            participant_raw_id=user_id,
            participant_kind="acs_user"
        )

        return ParticipantResponse(
            message="Participant removed successfully",
            user_id=user_id,
            success=True,
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )