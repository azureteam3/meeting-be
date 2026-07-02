# Translator Backend

## Run
uvicorn app.main:app --reload

## Migration
alembic revision --autogenerate -m "init"
alembic upgrade head

# Azure AI 기반 실시간 회의 지원 에이전트 백엔드

## 개요
FastAPI 기반 백엔드로, 회의 오디오를 Azure Speech로 전사하고 Azure Translator로 한국어 번역 후 DB에 저장하는 구조입니다.

## 주요 기능
- 세션 시작/종료 API
- transcript ingest API
- PostgreSQL 저장
- Azure Speech ConversationTranscriber 연동 구조
- Azure Translator 연동 구조
- WebSocket 기반 실시간 전송 구조

## 실행 방법
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 환경 변수
`.env.example` 참고

## 주요 엔드포인트
- `GET /health`
- `GET /health/db`
- `POST /sessions/start`
- `POST /sessions/stop/{session_id}`
- `POST /transcripts/ingest`
- `GET /transcripts`
- `WS /ws/{session_id}`