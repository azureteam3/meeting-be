from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "meeting-backend"
    APP_ENV: str = "dev"

    POSTGRES_URL: str
    ACS_CONNECTION_STRING: str
    ACS_PHONE_NUMBER: str 
    ACS_COGNITIVE_SERVICE_ENDPOINT: str 

    SPEECH_KEY: str = ""
    SPEECH_REGION: str = ""

    TRANSLATOR_KEY: str = ""
    TRANSLATOR_REGION: str = ""
    TRANSLATOR_ENDPOINT: str = "https://api.cognitive.microsofttranslator.com"

    TARGET_LANGUAGE: str = "ko"
    SPEECH_AUTO_DETECT_LANGUAGES: str = "ko-KR,en-US,ja-JP,zh-CN"
    TRANSLATOR_SOURCE_LANGUAGES: str = "en,ja,zh-Hans"

    ACS_CALLBACK_URL: str = "https://ict4meeting.azurewebsites.net/callbacks"
    AUDIO_WS_URL_TEMPLATE: str = "wss://ict4meeting.azurewebsites.net/audio/{session_id}"

    MIN_TEXT_LENGTH: int = 2
    MIN_CONFIDENCE: float = 0.7
    TRANSLATOR_TIMEOUT_SEC: int = 3
    MAX_RECONNECT_RETRIES: int = 5
    RECONNECT_DELAY_SEC: int = 3

    FILLER_WORDS: str = "uh,um,er,ah,음,어,그,저"

    @property
    def speech_auto_detect_languages(self) -> List[str]:
        return [x.strip() for x in self.SPEECH_AUTO_DETECT_LANGUAGES.split(",") if x.strip()]

    @property
    def translator_source_languages(self) -> List[str]:
        return [x.strip() for x in self.TRANSLATOR_SOURCE_LANGUAGES.split(",") if x.strip()]

    @property
    def filler_words(self) -> List[str]:
        return [x.strip() for x in self.FILLER_WORDS.split(",") if x.strip()]


settings = Settings()