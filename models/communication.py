from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import uuid

router = APIRouter(prefix="/sessions", tags=["Communication"])

# -------------------------
# 임시 DB
# -------------------------
sessions = {}


# -------------------------
# DTO
# -------------------------
class CreateSessionRequest(BaseModel):
    title: str
    host_id: str


class ParticipantRequest(BaseModel):
    user_id: str
    name: str


# -------------------------
# 회의 생성
# -------------------------
@router.post("")
def create_session(req: CreateSessionRequest):

    session_id = str(uuid.uuid4())

    sessions[session_id] = {
        "session_id": session_id,
        "title": req.title,
        "host_id": req.host_id,
        "participants": [],
        "status": "ACTIVE"
    }

    return sessions[session_id]


# -------------------------
# 회의 조회
# -------------------------
@router.get("/{session_id}")
def get_session(session_id: str):

    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    return sessions[session_id]


# -------------------------
# 회의 종료
# -------------------------
@router.delete("/{session_id}")
def delete_session(session_id: str):

    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    del sessions[session_id]

    return {
        "message": "Session deleted"
    }


# -------------------------
# 참가자 입장
# -------------------------
@router.post("/{session_id}/participants")
def add_participant(
    session_id: str,
    req: ParticipantRequest
):

    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    sessions[session_id]["participants"].append({
        "user_id": req.user_id,
        "name": req.name
    })

    return {
        "message": "Participant joined"
    }


# -------------------------
# 참가자 퇴장
# -------------------------
@router.delete("/{session_id}/participants/{user_id}")
def remove_participant(
    session_id: str,
    user_id: str
):

    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    participants = sessions[session_id]["participants"]

    sessions[session_id]["participants"] = [
        p for p in participants
        if p["user_id"] != user_id
    ]

    return {
        "message": "Participant removed"
    }


# -------------------------
# ACS Token
# -------------------------
@router.get("/{session_id}/token")
def get_token(session_id: str):

    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    # TODO
    # Azure Communication Service Token 발급

    return {
        "token": "TEMP_TOKEN"
    }