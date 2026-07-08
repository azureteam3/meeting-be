# AI Meeting Backend

FastAPI 기반 실시간 다국어 회의 백엔드입니다. 프론트에서 전달한 브라우저 마이크 오디오를 Azure Speech로 전사하고, 최종 자막을 DB에 저장한 뒤 Azure Translator와 Azure OpenAI 기반 에이전트 기능을 제공합니다.

## 주요 기능

### 1. 회의 세션 관리

- 회의방 단위 `meeting_id`와 사용자 접속 단위 `session_id`를 관리합니다.
- 세션 시작/종료 상태를 DB에 저장합니다.
- 실행 중인 세션의 WebSocket, STT 인스턴스, 사용자 메타데이터를 메모리에서 관리합니다.
- 같은 `meeting_id`에 연결된 여러 WebSocket으로 자막과 번역 결과를 브로드캐스트합니다.

관련 파일:

- `app/api/routes_session.py`
- `app/services/session_manager.py`
- `app/repositories/session_repository.py`

### 2. ACS 통신 연동

- Azure Communication Services 세션을 생성합니다.
- ACS 사용자 토큰을 발급합니다.
- 참가자 추가/삭제 API를 제공합니다.
- ACS 콜백과 오디오 WebSocket 게이트웨이 구조를 포함합니다.

관련 파일:

- `app/api/routes_communication.py`
- `app/api/routes_callbacks.py`
- `app/api/routes_websoket.py`
- `app/services/communication_service.py`
- `app/services/acs_audio_bridge.py`

### 3. 실시간 음성 인식

- 프론트 WebSocket `/ws/{session_id}`로 PCM16 mono 16kHz 오디오를 받습니다.
- WebSocket 연결 시 Azure Speech `ConversationTranscriber` 세션을 엽니다.
- Azure Speech의 `transcribing`, `transcribed` 이벤트를 받아 중간/최종 자막 이벤트로 변환합니다.
- 선택 언어는 WebSocket query 또는 `start_transcription` 메시지의 metadata로 저장됩니다.

흐름:

```text
Browser microphone
  -> WebSocket binary PCM16
  -> routes_stream.py
  -> SpeechAudioRouter
  -> SpeechTranscriberService
  -> Azure Speech ConversationTranscriber
  -> TranscriptProcessor
```

관련 파일:

- `app/api/routes_stream.py`
- `app/services/speech.py`
- `app/services/speech_transcriber.py`
- `app/services/transcript_processor.py`

### 4. 자막 정제 및 저장

- STT 원문을 공백 정리, filler word 제거, 문장부호 보정 후 `TranscriptEvent`로 변환합니다.
- `interim` 자막은 실시간 표시용으로 WebSocket에 push합니다.
- `final` 자막은 DB `transcript_records`에 저장합니다.
- 저장된 최종 자막은 AI 채팅, 회의 요약, 회의록 생성의 기준 데이터가 됩니다.

관련 파일:

- `app/services/transcript_processor.py`
- `app/services/transcript_service.py`
- `app/repositories/transcript_repository.py`
- `app/utils/text_cleaner.py`
- `app/utils/language_map.py`

### 5. 번역

- 최종 자막이 저장되면 `TranslationWorker`가 Azure Translator를 호출합니다.
- 현재 앱 언어 기준 `ko`, `en`, `ja`, `zh` 번역 결과를 생성합니다.
- 한국어 번역 결과는 `transcript_records.translated_text`에 저장합니다.
- 전체 번역 객체는 같은 `meeting_id`의 모든 WebSocket에 `translation_update`로 전송합니다.

관련 파일:

- `app/services/translator_service.py`
- `app/services/translation_worker.py`
- `app/services/transcript_service.py`

### 6. AI 채팅, 요약, 회의록

- Azure OpenAI function calling으로 회의 자막 조회, 참가자 조회, 키워드 검색, 저장된 요약 조회를 수행합니다.
- “회의록 요약해줘” 같은 요약 의도는 저장된 요약 스냅샷을 사용하거나 새 자막만 증분 반영합니다.
- 회의록은 JSON으로 저장할 수 있고, `.docx` 파일로 다운로드할 수 있습니다.
- 조회 범위는 경로의 `session_id` 값으로 전달된 회의 식별자이며, 내부적으로 `transcript_records.meeting_id`를 기준으로 조회합니다.

관련 파일:

- `app/api/routes_agent.py`
- `app/services/agent_service.py`
- `app/repositories/agent_repository.py`
- `app/schemas/agent.py`

## 전체 처리 흐름

```text
1. 프론트가 /communication/token 으로 ACS 토큰 발급
2. 프론트가 /sessions/start 로 meeting_id/session_id 등록
3. 프론트가 WS /ws/{session_id}?username=...&language=... 연결
4. 백엔드가 SpeechAudioRouter를 통해 Azure STT 세션 시작
5. 프론트가 마이크 PCM16 오디오를 WebSocket binary로 전송
6. Azure Speech가 interim/final transcript 이벤트 발생
7. TranscriptProcessor가 텍스트 정제 및 TranscriptEvent 생성
8. TranscriptService가 같은 meeting_id의 WebSocket에 원문 자막 push
9. final 자막은 DB 저장 후 TranslationWorker가 다국어 번역
10. 번역 결과를 DB 업데이트 및 WebSocket translation_update로 push
11. Agent API가 저장된 transcript_records를 조회해 요약/회의록/질문응답 생성
```

## API 요약

### Health

| Method | Path | 설명 |
| --- | --- | --- |
| `GET` | `/` | 서버 상태 확인 |
| `GET` | `/health` | 헬스 체크 |

### Session

| Method | Path | 설명 |
| --- | --- | --- |
| `POST` | `/sessions/start` | 회의 세션 시작 |
| `POST` | `/sessions/stop/{session_id}` | 회의 세션 종료 |
| `GET` | `/sessions` | 세션 목록 조회 |
| `POST` | `/sessions/{session_id}/audio` | base64 오디오 chunk 수신 |

`POST /sessions/start`

```json
{
  "meeting_id": "room-a",
  "session_id": "session-123"
}
```

### Communication

| Method | Path | 설명 |
| --- | --- | --- |
| `POST` | `/communication/sessions` | ACS 세션 생성 |
| `GET` | `/communication/sessions/{session_id}` | ACS 세션 조회 |
| `DELETE` | `/communication/sessions/{session_id}` | ACS 세션 삭제 |
| `POST` | `/communication/token` | ACS 사용자 토큰 발급 |
| `POST` | `/communication/sessions/{session_id}/participants` | ACS 참가자 추가 |
| `DELETE` | `/communication/sessions/{session_id}/participants/{user_id}` | ACS 참가자 삭제 |

### Transcript

| Method | Path | 설명 |
| --- | --- | --- |
| `POST` | `/transcripts/ingest` | 텍스트 transcript 수동 ingest |
| `GET` | `/transcripts?session_id=...` | 저장된 transcript 조회 |

`POST /transcripts/ingest`

```json
{
  "meeting_id": "room-a",
  "session_id": "session-123",
  "event_type": "final",
  "speaker": "사용자",
  "speaker_id": "speaker-1",
  "text": "안녕하세요.",
  "source_language": "ko-KR",
  "confidence": 0.95
}
```

### Realtime WebSocket

| Method | Path | 설명 |
| --- | --- | --- |
| `WS` | `/ws/{session_id}` | 프론트 마이크 오디오 및 실시간 자막 스트림 |
| `WS` | `/ws/audio/{session_id}` | ACS 오디오 WebSocket 게이트웨이 |

프론트 WebSocket 예시:

```text
ws://localhost:8000/ws/{session_id}?username=홍길동&language=ko
```

수신 JSON 메시지:

```json
{
  "type": "join",
  "payload": {
    "username": "홍길동",
    "language": "ko"
  }
}
```

```json
{
  "type": "start_transcription",
  "payload": {
    "language": "ko",
    "sampleRate": 16000,
    "format": "pcm_s16le",
    "channels": 1
  }
}
```

오디오는 JSON이 아니라 WebSocket binary로 전송합니다.

서버 송신 메시지:

```json
{
  "type": "transcript",
  "payload": {
    "id": "seg-xxxx",
    "original": "안녕하세요.",
    "translated": null,
    "language": "ko",
    "speaker_id": "unknown",
    "username": "홍길동",
    "is_final": true
  }
}
```

```json
{
  "type": "translation_update",
  "payload": {
    "id": "seg-xxxx",
    "translated": "안녕하세요.",
    "translations": {
      "ko": "안녕하세요.",
      "en": "Hello.",
      "ja": "こんにちは。",
      "zh": "你好。"
    }
  }
}
```

### Agent

| Method | Path | 설명 |
| --- | --- | --- |
| `POST` | `/agent/sessions/{session_id}/query` | AI 채팅 질의 |
| `GET` | `/agent/sessions/{session_id}/summary` | 현재 회의 요약 조회/생성 |
| `GET` | `/agent/sessions/{session_id}/action-items` | 액션 아이템 조회 |
| `GET` | `/agent/sessions/{session_id}/decisions` | 의사결정 조회 |
| `GET` | `/agent/sessions/{session_id}/minutes` | 회의록 조회/생성 |
| `GET` | `/agent/sessions/{session_id}/minutes/{minutes_id}` | 저장된 회의록 단건 조회 |
| `GET` | `/agent/sessions/{session_id}/minutes/download` | 회의록 `.docx` 다운로드 |

`POST /agent/sessions/{session_id}/query`

```json
{
  "userId": "user-1",
  "message": "회의록 요약해줘",
  "responseLanguage": "ko"
}
```

## 데이터베이스

앱 시작 시 `Base.metadata.create_all(bind=engine)`로 테이블을 생성합니다.

### `meeting_sessions`

회의 세션의 시작/종료 상태를 저장합니다.

- `meeting_id`
- `session_id`
- `status`
- `created_at`

### `transcript_records`

최종 transcript와 번역 상태를 저장합니다.

- `segment_id`
- `meeting_id`
- `session_id`
- `event_type`
- `speaker`, `speaker_id`
- `original_text`, `cleaned_text`, `translated_text`
- `original_language`, `target_language`
- `confidence`, `is_reliable`, `needs_review`
- `offset_ms`, `duration_ms`
- `created_at`

### `meeting_summary_snapshot`

AI 요약 스냅샷을 append-only 방식으로 저장합니다.

- `meeting_id`
- `version`
- `coverage_to_seq`
- `summary_json`
- `created_at`

### `meeting_chat_message`

AI 채팅 이력을 저장하기 위한 테이블입니다.

- `meeting_id`
- `sender_type`
- `content`
- `response_type`
- `created_at`

### `meeting_minutes`

생성된 회의록 JSON을 저장합니다.

- `id`
- `meeting_id`
- `minutes_json`
- `created_at`

## 환경 변수

`.env`에 다음 값이 필요합니다.

```env
POSTGRES_URL=

ACS_CONNECTION_STRING=
ACS_PHONE_NUMBER=
ACS_COGNITIVE_SERVICE_ENDPOINT=
ACS_CALLBACK_URL=
AUDIO_WS_URL_TEMPLATE=

SPEECH_KEY=
SPEECH_REGION=
SPEECH_AUTO_DETECT_LANGUAGES=ko-KR,en-US,ja-JP,zh-CN

TRANSLATOR_KEY=
TRANSLATOR_REGION=
TRANSLATOR_ENDPOINT=https://api.cognitive.microsofttranslator.com
TARGET_LANGUAGE=ko
TRANSLATOR_SOURCE_LANGUAGES=en,ja,zh-Hans

AZURE_AI_PROJECT_ENDPOINT=
AZURE_AI_API_KEY=
AZURE_AI_DEPLOYMENT=

AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_DEPLOYMENT=
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

`AZURE_AI_*`와 `AZURE_OPENAI_*`는 값이 채워진 쪽을 우선 사용합니다.

## 실행 방법

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

서버 기본 주소:

```text
http://localhost:8000
```

Swagger 문서:

```text
http://localhost:8000/docs
```

## 테스트

```bash
pytest
```

현재 테스트 파일:

- `tests/test_processor.py`
- `tests/test_text_cleaner.py`

## 개발 메모

- 프론트의 실시간 WebSocket은 `session_id`로 연결하지만, 자막/번역 브로드캐스트는 같은 `meeting_id` 기준으로 전송합니다.
- `interim` transcript는 실시간 자막 표시용이고 DB 저장 대상은 아닙니다.
- `final` transcript만 DB 저장 및 번역 작업 대상입니다.
- AI 채팅/요약/회의록은 `transcript_records.meeting_id` 기준으로 회의 데이터를 조회합니다.
- 같은 `meeting_id`를 재사용하면 이전 회의 transcript가 함께 조회될 수 있습니다. 테스트 시 이전 데이터가 섞이면 새로운 `meeting_id`를 사용하거나 DB 데이터를 정리해야 합니다.
- 백엔드 코드를 수정한 뒤에는 실행 중인 FastAPI 서버를 재시작해야 STT/라우터 변경이 반영됩니다.

