from __future__ import annotations

from datetime import timedelta
from typing import Any

from azure.communication.callautomation import (
    AudioFormat,
    CallAutomationClient,
    CommunicationUserIdentifier,
    MediaStreamingAudioChannelType,
    MediaStreamingContentType,
    MediaStreamingOptions,
    PhoneNumberIdentifier,
    StreamingTransportType,
)
from azure.communication.identity import (
    CommunicationIdentityClient,
    CommunicationTokenScope,
)

from app.models.conference_session import ConferenceSession, ParticipantKind
from app.services.session_store import SessionStore

class ACSCommunicationService:
    """Azure Communication Services 핵심 연동 및 래핑 서비스 클래스"""
    def __init__(self, connection_string: str, callback_url: str, audio_ws_url_template: str) -> None:
        self.call_client = CallAutomationClient.from_connection_string(connection_string)
        self.identity_client = CommunicationIdentityClient.from_connection_string(connection_string)
        self.callback_url = callback_url
        self.audio_ws_url_template = audio_ws_url_template
        self.sessions = SessionStore()

    def create_session(self) -> ConferenceSession:
        return self.sessions.create()

    def get_session(self, session_id: str) -> ConferenceSession:
        return self.sessions.get(session_id)

    def delete_session(self, session_id: str, *, hang_up: bool = False) -> None:
        session = self.sessions.get(session_id)
        if hang_up and session.call_connection_id:
            try:
                self.call_client.get_call_connection(session.call_connection_id).hang_up(
                    is_for_everyone=True
                )
            except Exception as e:
                print(f"[ACS] 전화 끊기 실패: {e}")
        self.sessions.delete(session_id)

    def issue_token(self, expires_in_hours: int = 24) -> dict[str, Any]:
        """정의된 ACS Identity Client를 사용해 VoIP 통화 인증 토큰 발급"""
        user, token = self.identity_client.create_user_and_token(
            scopes=[CommunicationTokenScope.VOIP],
            token_expires_in=timedelta(hours=expires_in_hours),
        )
        return {
            "identity": user.properties["id"],
            "token": token.token,
            "expires_on": token.expires_on,
        }

    def create_call(
        self,
        *,
        session_id: str,
        target_raw_id: str,
        target_kind: ParticipantKind = "acs_user",
        source_phone_number: str | None = None,
    ) -> ConferenceSession:
        """아웃바운드 전화를 개설하여 실시간 오디오 스트림 스트리밍 채널 활성화"""
        session = self.sessions.get(session_id)

        result = self.call_client.create_call(
            target_participant=self._identifier(target_raw_id, target_kind),
            callback_url=self._callback_url_for_session(session_id),
            source_caller_id_number=PhoneNumberIdentifier(source_phone_number) if source_phone_number else None,
            media_streaming=self._media_streaming_options(session_id, start=True),
            operation_context=session_id,
        )

        self._apply_call_result(session, result)
        return session

    def answer_call(self, *, session_id: str, incoming_call_context: str) -> ConferenceSession:
        """인바운드 전화를 수락하며 즉시 실시간 오디오 스트리밍을 활성화"""
        session = self.sessions.get(session_id)

        result = self.call_client.answer_call(
            incoming_call_context=incoming_call_context,
            callback_url=self._callback_url_for_session(session_id),
            media_streaming=self._media_streaming_options(session_id, start=True),
            operation_context=session_id,
        )

        self._apply_call_result(session, result)
        return session

    def connect_call(self, *, session_id: str, server_call_id: str) -> ConferenceSession:
        """통화 세션 브릿징 연동"""
        session = self.sessions.get(session_id)

        result = self.call_client.connect_call(
            callback_url=self._callback_url_for_session(session_id),
            server_call_id=server_call_id,
            media_streaming=self._media_streaming_options(session_id, start=True),
            operation_context=session_id,
        )

        self._apply_call_result(session, result)
        return session

    def get_call(self, session_id: str) -> dict[str, Any]:
        session = self.sessions.get(session_id)
        client = self.call_client.get_call_connection(self._require_call_connection_id(session))
        return client.get_call_properties().as_dict()

    def add_participant(
        self,
        *,
        session_id: str,
        participant_raw_id: str,
        participant_kind: ParticipantKind = "acs_user",
        source_phone_number: str | None = None,
    ) -> dict[str, Any]:
        """진행 중인 통화에 새로운 제3의 참가자 추가"""
        session = self.sessions.get(session_id)
        client = self.call_client.get_call_connection(self._require_call_connection_id(session))

        result = client.add_participant(
            self._identifier(participant_raw_id, participant_kind),
            source_caller_id_number=PhoneNumberIdentifier(source_phone_number) if source_phone_number else None,
            operation_context=session_id,
        )
        
        session.participants.append({"user_id": participant_raw_id, "kind": participant_kind})
        return result.as_dict() if hasattr(result, "as_dict") else {"result": result}

    def remove_participant(
        self,
        *,
        session_id: str,
        participant_raw_id: str,
        participant_kind: ParticipantKind = "acs_user",
    ) -> None:
        """특정 세션 참여자 연결 강제 종료 및 퇴장 처리"""
        session = self.sessions.get(session_id)
        client = self.call_client.get_call_connection(self._require_call_connection_id(session))

        client.remove_participant(
            self._identifier(participant_raw_id, participant_kind),
            operation_context=session_id,
        )
        session.participants = [p for p in session.participants if p["user_id"] != participant_raw_id]

    def start_media_streaming(self, *, session_id: str) -> None:
        """통화 도중 수동으로 오디오 스트리밍 채널 활성화"""
        session = self.sessions.get(session_id)
        client = self.call_client.get_call_connection(self._require_call_connection_id(session))

        client.start_media_streaming(
            operation_context=f"start-media-streaming:{session_id}"
        )

    def stop_media_streaming(self, *, session_id: str) -> None:
        """통화 진행을 유지한 채 오디오 스트리밍 데이터 수신 정지"""
        session = self.sessions.get(session_id)
        client = self.call_client.get_call_connection(self._require_call_connection_id(session))

        client.stop_media_streaming(
            operation_context=f"stop-media-streaming:{session_id}"
        )

    def _media_streaming_options(self, session_id: str, *, start: bool) -> MediaStreamingOptions:
        """웹소켓 프로토콜 스트리밍 상세 규격 빌더 (기본 16K Mono PCM 세팅)"""
        return MediaStreamingOptions(
            transport_url=self.audio_ws_url_template.format(session_id=session_id),
            transport_type=StreamingTransportType.WEBSOCKET,
            content_type=MediaStreamingContentType.AUDIO,
            audio_channel_type=MediaStreamingAudioChannelType.MIXED,
            start_media_streaming=start,
            enable_bidirectional=True,
            audio_format=AudioFormat.PCM16_K_MONO,
            enable_dtmf_tones=True,
        )

    def _callback_url_for_session(self, session_id: str) -> str:
        separator = "&" if "?" in self.callback_url else "?"
        return f"{self.callback_url}{separator}session_id={session_id}"

    @staticmethod
    def _identifier(raw_id: str, kind: ParticipantKind):
        if kind == "phone":
            return PhoneNumberIdentifier(raw_id)
        return CommunicationUserIdentifier(raw_id)

    @staticmethod
    def _apply_call_result(session: ConferenceSession, result: Any) -> None:
        session.call_connection_id = getattr(result, "call_connection_id", None)
        session.server_call_id = getattr(result, "server_call_id", None)
        session.correlation_id = getattr(result, "correlation_id", None)
        session.state = "connecting"

    @staticmethod
    def _require_call_connection_id(session: ConferenceSession) -> str:
        if not session.call_connection_id:
            raise ValueError("이 세션에는 아직 취득된 call_connection_id가 부재합니다.")
        return session.call_connection_id