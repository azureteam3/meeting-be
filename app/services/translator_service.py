import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from app.config import settings


class TranslatorService:
    
    def __init__(self):
        self.endpoint = f"{settings.TRANSLATOR_ENDPOINT}/translate"
        self.headers = {
            "Ocp-Apim-Subscription-Key": settings.TRANSLATOR_KEY,
            "Ocp-Apim-Subscription-Region": settings.TRANSLATOR_REGION,
            "Content-Type": "application/json",
        }

        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

        def translate_to_korean(self, text: str, source_language: str | None) -> str:

            if not text:
                return text

            if source_language == "ko":
                return text
            print(f"[Translator] {source_language} -> ko : {text}")

            params = {
                "api-version": "3.0",
                "to": "ko",
            }

            if source_language:
                params["from"] = source_language

            body = [{"text": text}]
            
            try:
                response = self.session.post(
                    self.endpoint,
                    params=params,
                    headers=self.headers,
                    json=body,
                    timeout=settings.TRANSLATOR_TIMEOUT_SEC,
                )
                response.raise_for_status()
                data = response.json()
                
                if not data:
                    return text

                translations = data[0].get("translations")

                if not translations:
                    return text

                translated = translations[0].get("text", text)

                print(f"[Translator Success] {translated}")

                return translated
            except Exception as e:
                print("[Translator Error]", e)

                return text