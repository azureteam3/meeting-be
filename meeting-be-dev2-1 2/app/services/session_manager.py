from app.repositories.session_repository import SessionRepository


class SessionManager:
    def __init__(self):
        self.repository = SessionRepository()
        self.runtime_sessions = {}

    def start_session(self, meeting_id: str, session_id: str):
        db_result = self.repository.create_session(meeting_id, session_id)

        if session_id not in self.runtime_sessions:
            self.runtime_sessions[session_id] = {
                "meeting_id": meeting_id,
                "session_id": session_id,
                "transcriber": None,
                "websockets": set(),
                "status": "started",
            }

        return db_result

    def stop_session(self, session_id: str):
        runtime = self.runtime_sessions.get(session_id)
        if runtime and runtime.get("transcriber"):
            try:
                runtime["transcriber"].stop()
            except Exception:
                pass

        db_result = self.repository.stop_session(session_id)

        if session_id in self.runtime_sessions:
            del self.runtime_sessions[session_id]

        return db_result

    def list_sessions(self):
        return self.repository.list_sessions()

    def get_runtime(self, session_id: str):
        return self.runtime_sessions.get(session_id)

    def set_transcriber(self, session_id: str, transcriber):
        if session_id in self.runtime_sessions:
            self.runtime_sessions[session_id]["transcriber"] = transcriber

    def set_metadata(self, session_id: str, metadata: dict):
        if session_id in self.runtime_sessions:
            current = self.runtime_sessions[session_id].setdefault(
                "metadata",
                {},
            )
            current.update(metadata)

    def get_metadata(self, session_id: str):
        runtime = self.runtime_sessions.get(session_id)
        if not runtime:
            return {}
        return runtime.get("metadata", {})

    def add_websocket(self, session_id: str, websocket):
        if session_id in self.runtime_sessions:
            self.runtime_sessions[session_id]["websockets"].add(websocket)

    def remove_websocket(self, session_id: str, websocket):
        if session_id in self.runtime_sessions:
            self.runtime_sessions[session_id]["websockets"].discard(websocket)

    def get_websockets(self, session_id: str):
        runtime = self.runtime_sessions.get(session_id)
        if not runtime:
            return set()
        return runtime["websockets"]

    def get_websockets_by_meeting_id(self, meeting_id: str):
        websockets = set()

        for runtime in self.runtime_sessions.values():
            if runtime.get("meeting_id") == meeting_id:
                websockets.update(runtime.get("websockets", set()))

        return websockets

    def remove_websocket_from_all(self, websocket):
        for session_id in list(self.runtime_sessions.keys()):
            self.remove_websocket(session_id, websocket)

session_manager = SessionManager()
