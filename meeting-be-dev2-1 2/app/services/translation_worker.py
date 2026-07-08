class TranslationWorker:
    TARGET_LANGUAGES = {
        "ko": "ko",
        "en": "en",
        "ja": "ja",
        "zh": "zh-Hans",
    }

    def __init__(self, translator, repo, session_manager):
        self.translator = translator
        self.repo = repo
        self.session_manager = session_manager

    async def run(self, event):
        try:
            translations = {}

            for app_language, translator_language in self.TARGET_LANGUAGES.items():
                translations[app_language] = self.translator.translate(
                    text=event.cleaned_text,
                    source_language=event.original_language,
                    target_language=translator_language,
                )

            ko = translations.get("ko", event.cleaned_text)

            # 1. DB update
            self.repo.update_translation(
                segment_id=event.segment_id,
                translated_text=ko
            )

            # 2. websocket push
            websockets = self.session_manager.get_websockets_by_meeting_id(
                event.meeting_id
            )

            for ws in websockets:
                await ws.send_json({
                    "type": "translation_update",
                    "payload": {
                        "id": event.segment_id,
                        "translated": ko,
                        "translations": translations,
                    }
                })

            return ko

        except Exception as e:
            print("[Translation Worker Error]", e)
            return None
