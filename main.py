import sys
import os
# 현재 실행되는 파일(main.py)의 디렉토리를 파이썬 라이브러리 검색 경로에 강제 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI

from app.api.routes_health import router as health_router
from app.api.routes_session import router as session_router
from app.api.routes_transcript import router as transcript_router
from app.api.routes_stream import router as stream_router
from app.db.postgres import Base, engine
from app.db import models
# [수정] app/api/ 폴더 하위의 실제 파일명으로 정밀 매칭하여 import
from app.api.routes_communication import router as communication_router
from app.api.routes_callbacks import router as callbacks_router
from app.api.routes_websoket import router as websocket_router
from app.api.routes_communication import communication_service

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Azure Meeting Backend MVP")

# FastAPI 전역 상태에 초기화된 ACS 서비스 인스턴스 등록
app.state.acs = communication_service

app.include_router(health_router)
app.include_router(session_router)
app.include_router(transcript_router)
app.include_router(stream_router)
# 분리된 모든 라우터(통화 관리, 웹훅 콜백, 실시간 오디오 웹소켓)를 서버에 등록
app.include_router(communication_router)
app.include_router(callbacks_router)
app.include_router(websocket_router)

@app.get("/")
def read_root():
    return {"status": "running", "message": "ACS Audio Pipeline Server is active"}

