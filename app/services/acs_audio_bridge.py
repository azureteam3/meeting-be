import base64


class ACSAudioBridge:
    def __init__(self, transcriber):
        self.transcriber = transcriber

    def ingest_base64_audio(self, audio_base64: str):
        pcm_bytes = base64.b64decode(audio_base64)
        self.transcriber.push_audio(pcm_bytes)

    def ingest_pcm_bytes(self, pcm_bytes: bytes):
        self.transcriber.push_audio(pcm_bytes)