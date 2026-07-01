from app.db.postgres import SessionLocal
from app.db.models import MeetingSession


class SessionRepository:
    def create_session(self, meeting_id: str, session_id: str):
        db = SessionLocal()
        try:
            existing = db.query(MeetingSession).filter(MeetingSession.session_id == session_id).first()
            if existing:
                return {
                    "message": "already started",
                    "meeting_id": existing.meeting_id,
                    "session_id": existing.session_id,
                    "status": existing.status,
                    "created_at": existing.created_at,
                }

            row = MeetingSession(
                meeting_id=meeting_id,
                session_id=session_id,
                status="started",
            )
            db.add(row)
            db.commit()
            db.refresh(row)

            return {
                "message": "started",
                "meeting_id": row.meeting_id,
                "session_id": row.session_id,
                "status": row.status,
                "created_at": row.created_at,
            }
        finally:
            db.close()

    def stop_session(self, session_id: str):
        db = SessionLocal()
        try:
            row = db.query(MeetingSession).filter(MeetingSession.session_id == session_id).first()
            if not row:
                return {
                    "message": "not found",
                    "session_id": session_id,
                }

            row.status = "stopped"
            db.commit()
            db.refresh(row)

            return {
                "message": "stopped",
                "meeting_id": row.meeting_id,
                "session_id": row.session_id,
                "status": row.status,
                "created_at": row.created_at,
            }
        finally:
            db.close()

    def list_sessions(self):
        db = SessionLocal()
        try:
            rows = db.query(MeetingSession).order_by(MeetingSession.created_at.desc()).all()
            return [
                {
                    "meeting_id": row.meeting_id,
                    "session_id": row.session_id,
                    "status": row.status,
                    "created_at": row.created_at,
                }
                for row in rows
            ]
        finally:
            db.close()