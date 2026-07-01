from fastapi import FastAPI
from models.communication import router as communication_router

app = FastAPI()

app.include_router(communication_router)