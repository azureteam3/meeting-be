from fastapi import FastAPI
from app.api.routes_health import router as health_router
from app.api.routes_session import router as session_router
from app.api.routes_transcript import router as transcript_router
from app.api.routes_stream import router as stream_router
from app.db.postgres import Base, engine
from app.db import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Azure Meeting Backend MVP")

app.include_router(health_router)
app.include_router(session_router)
app.include_router(transcript_router)
app.include_router(stream_router)