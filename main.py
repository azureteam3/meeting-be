from fastapi import FastAPI

# [수정] app/api/ 폴더 하위의 실제 파일명으로 정밀 매칭하여 import
from app.api.routes_communication import router as communication_router
from app.api.routes_callbacks import router as callbacks_router
from app.api.routes_websoket import router as websocket_router
from app.api.routes_communication import communication_service

app = FastAPI(title="Azure CallBot Backend Engine")

# FastAPI 전역 상태에 초기화된 ACS 서비스 인스턴스 등록
app.state.acs = communication_service

# 분리된 모든 라우터(통화 관리, 웹훅 콜백, 실시간 오디오 웹소켓)를 서버에 등록
app.include_router(communication_router)
app.include_router(callbacks_router)
app.include_router(websocket_router)

@app.get("/")
def read_root():
    return {"status": "running", "message": "ACS Audio Pipeline Server is active"}

