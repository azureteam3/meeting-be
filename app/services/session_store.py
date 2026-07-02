from threading import RLock
from uuid import uuid4
from app.models.conference_session import ConferenceSession

class SessionStore:
    """스레드 안정성(Thread-safe)을 보장하는 인메모리 세션 관리 저장소"""
    def __init__(self) -> None:
        self._items: dict[str, ConferenceSession] = {}
        self._lock = RLock()

    def create(self) -> ConferenceSession:
        with self._lock:
            session = ConferenceSession(id=str(uuid4()))
            self._items[session.id] = session
            return session

    def get(self, session_id: str) -> ConferenceSession:
        with self._lock:
            if session_id not in self._items:
                raise KeyError(f"세션 {session_id}을(를) 찾을 수 없습니다.")
            return self._items[session_id]

    def delete(self, session_id: str) -> None:
        with self._lock:
            if session_id in self._items:
                del self._items[session_id]