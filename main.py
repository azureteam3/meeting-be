import asynccontextmanager
 
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
 
from app.api.routes_health import router as health_router
from app.api.routes_session import router as session_router
from app.api.routes_transcript import router as transcript_router
from app.api.routes_stream import router as stream_router
from app.api.routes_communication import router as communication_router
from app.api.routes_callbacks import router as callbacks_router
from app.api.routes_websoket import router as websocket_router
from app.api.routes_communication import communication_service
 
from app.db.postgres import Base, engine
from app.db import models
 
 
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    app.state.acs = communication_service
    yield
 
 
app = FastAPI(
    title="Azure Meeting Backend MVP",
    lifespan=lifespan
)
 
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
 
app.include_router(health_router)
app.include_router(session_router)
app.include_router(transcript_router)
app.include_router(stream_router)
app.include_router(communication_router)
app.include_router(callbacks_router)
app.include_router(websocket_router)
 
 
@app.get("/")
def read_root():
    return {"status": "running", "message": "ACS Audio Pipeline Server is active"}