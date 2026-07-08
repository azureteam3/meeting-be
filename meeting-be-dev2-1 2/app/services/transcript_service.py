from app.services.translation_worker import TranslationWorker
from app.services.session_manager import session_manager
from app.repositories.transcript_repository import TranscriptRepository
from app.services.translator_service import TranslatorService


class TranscriptService:

    def __init__(self):
        self.repo = TranscriptRepository()
        self.translator = TranslatorService()

        self.worker = TranslationWorker(
            translator=self.translator,
            repo=self.repo,
            session_manager=session_manager
        )

        self.session_manager = session_manager

    async def handle_event(self, event):
        """
        전체 pipeline 중앙 제어
        """
        metadata = self.session_manager.get_metadata(event.session_id)
        username = metadata.get("username")

        if username and not event.speaker:
            event.speaker = username

        # 1️⃣ 원문 즉시 push
        await self._push_original(event)

        # 2️⃣ final이면 번역 처리
        if event.event_type == "final":
            self.repo.save_event(event)
            await self.worker.run(event)

        # 3️⃣ summary routing (나중 확장)
        if event.is_final_for_summary:
            self._route_summary(event)

    async def _push_original(self, event):
        websockets = self.session_manager.get_websockets_by_meeting_id(
            event.meeting_id
        )
        metadata = self.session_manager.get_metadata(event.session_id)
        username = metadata.get("username") or event.speaker

        payload = {
            "type": "transcript",
            "payload": {
                "id": event.segment_id,
                "original": event.cleaned_text,
                "translated": None,
                "language": event.original_language,
                "speaker_id": event.speaker_id,
                "username": username,
                "is_final": event.event_type == "final"
            }
        }

        dead = []

        for ws in websockets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.session_manager.remove_websocket_from_all(ws)

    async def push_translation(self, event, ko: str, translations=None):
        websockets = self.session_manager.get_websockets_by_meeting_id(
            event.meeting_id
        )

        payload = {
            "type": "translation_update",
            "payload": {
                "id": event.segment_id,
                "translated": ko,
                "translations": translations or {"ko": ko},
            }
        }

        for ws in websockets:
            try:
                await ws.send_json(payload)
            except Exception:
                pass

    def _route_summary(self, event):
        """
        나중에 Foundry / GPT 요약 붙일 자리
        """
        pass

transcript_service = TranscriptService()
