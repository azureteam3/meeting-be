class TranslationWorker:
    def __init__(self, translator, repo, session_manager):
        self.translator = translator
        self.repo = repo
        self.session_manager = session_manager

    async def run(self, event):
        try:
            ko = self.translator.translate_to_korean(
                text=event.cleaned_text,
                source_language=event.original_language
            )

            # 1. DB update
            self.repo.update_translation(
                segment_id=event.segment_id,
                translated_text=ko
            )

            # 2. websocket push
            websockets = self.session_manager.get_websockets(event.session_id)

            for ws in websockets:
                await ws.send_json({
                    "type": "translation_update",
                    "payload": {
                        "id": event.segment_id,
                        "translated": ko
                    }
                })

            return ko

        except Exception as e:
            print("[Translation Worker Error]", e)
            return None