import asyncio
from typing import Any
from app.services.speech_transcriber import SpeechTranscriberService

class SpeechAudioRouter:
    """
    실시간 웹소켓 라우터(routes_websoket.py)와 
    Azure STT 스트리밍 서비스(SpeechTranscriberService)를 중계하는 라우터 클래스
    """
    def __init__(self) -> None:
        # 여러 통화 세션이 동시에 들어올 수 있으므로 세션별로 트랜스크라이버를 관리합니다.
        self._active_transcribers: dict[str, SpeechTranscriberService] = {}

    async def open_session(self, session_id: str, call_connection_id: str | None, correlation_id: str | None) -> None:
        """웹소켓이 연결되었을 때 호출되어 STT 변환 서비스를 초기화하고 시작합니다."""
        print(f"[SpeechRouter] 세션 오픈 -> STT 엔진 가동: SessionID={session_id}")
        
        # 콜백 결과나 데이터를 외부 인터페이스로 내보낼 실시간 emit 핸들러 예시
        def handle_emit(payload: dict[str, Any]):
            print(f"[실시간 자막 유입] {payload.get('type')} -> {payload.get('text')}")
            # 여기에 프론트엔드나 클라이언트로 자막을 쏘아주는 코드(예: 다른 웹소켓 전송 등)를 연동합니다.

        #  서비스 인스턴스 생성
        # meeting_id가 따로 정의되지 않았다면 예시로 session_id를 함께 바인딩합니다.
        transcriber = SpeechTranscriberService(
            meeting_id=session_id, 
            session_id=session_id, 
            on_emit=handle_emit
        )
        
        # Azure STT 인식 시작 실행
        transcriber.start()
        
        # 라우터 관리 대장에 등록
        self._active_transcribers[session_id] = transcriber

    async def set_metadata(self, session_id: str, metadata: dict[str, Any]) -> None:
        """오디오 메타데이터 정보 수신 처리"""
        print(f"[SpeechRouter] 메타데이터 매핑: SessionID={session_id}, Info={metadata}")

    async def push_pcm(self, session_id: str, pcm: bytes, participant_raw_id: str | None, timestamp: str | None) -> None:
        """소연님의 웹소켓에서 base64 디코딩되어 넘어온 순수 PCM 바이트를 팀원분 서비스로 밀어넣어 줍니다."""
        transcriber = self._active_transcribers.get(session_id)
        if transcriber:
            #  push_audio 메서드 호출!
            transcriber.push_audio(pcm)
        else:
            print(f"[SpeechRouter] 경고: 활성화되지 않은 세션의 오디오 유입 차단: {session_id}")

    async def push_dtmf(self, session_id: str, data: dict[str, Any]) -> None:
        """전화 키패드 입력(DTMF) 이벤트 수신 처리"""
        print(f"[SpeechRouter] DTMF 수신: SessionID={session_id}, Key={data.get('tone')}")

    async def close_session(self, session_id: str) -> None:
        """웹소켓 연결이 해제되었을 때 안전하게 Azure STT 리소스를 닫고 해제합니다."""
        print(f"[SpeechRouter] 세션 종료 -> STT 엔진 클린업: SessionID={session_id}")
        transcriber = self._active_transcribers.pop(session_id, None)
        if transcriber:
            #  stop 메서드 호출하여 push_stream 닫기 보장
            transcriber.stop()


# routes_websoket.py에서 임포트하여 전역으로 사용할 라우터 싱글톤 인스턴스 객체 선언
speech_audio_router = SpeechAudioRouter()