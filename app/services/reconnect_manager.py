import time
from app.config import settings


class ReconnectManager:
    def __init__(self):
        self.retry_count = 0

    def reset(self):
        self.retry_count = 0

    def can_retry(self) -> bool:
        return self.retry_count < settings.MAX_RECONNECT_RETRIES

    def wait_and_increment(self):
        self.retry_count += 1
        time.sleep(settings.RECONNECT_DELAY_SEC)