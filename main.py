from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_health import router as health_router
from app.api.routes_session import router as session_router
from app.api.routes_transcript import router as transcript_router
from app.api.routes_stream import router as stream_router
from app.api.routes_communication import router as communication_router
from app.api.routes_callbacks import router as callbacks_router
from app.api.routes_websoket import router as websocket_router
from app.api.routes_agent import router as agent_router
from app.api.routes_communication import communication_service

from app.db.postgres import Base, engine
from app.db import models

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서비스 시작 시 DB 테이블 동기화 구성
    Base.metadata.create_all(bind=engine)
    # FastAPI 전역 상태에 초기화된 ACS 서비스 인스턴스 등록
    app.state.acs = communication_service
    yield


app = FastAPI(
    title="Azure Meeting Backend MVP",
    lifespan=lifespan
)

# 프론트엔드(Vite 표준 포트 5173) 연동을 위한 CORS 허용 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 분리된 모든 라우터들을 서버에 순서대로 등록
app.include_router(health_router)
app.include_router(session_router)
app.include_router(transcript_router)
app.include_router(stream_router)
app.include_router(communication_router)
app.include_router(callbacks_router)
app.include_router(websocket_router)
app.include_router(agent_router)


@app.get("/")
def read_root():
    return {"status": "running", "message": "ACS Audio Pipeline Server is active"}
