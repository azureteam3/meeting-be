"""
app/schemas/agent.py - 에이전트 채팅 질의 API의 요청/응답 형식 (명세서 §4.2).

프론트 계약을 지키려고 camelCase 필드명(userId, responseLanguage, queryId)을 유지한다.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ContextRange(BaseModel):
    # 'from'은 파이썬 예약어라 별칭(alias)으로 받는다 ({"from": ..., "to": ...})
    from_: datetime = Field(alias="from")
    to: datetime


class QueryRequest(BaseModel):
    userId: str
    message: str
    contextRange: ContextRange | None = None   # 선택: 특정 시간 범위만 참조
    responseLanguage: str = "ko"               # 응답 언어


class QueryResponse(BaseModel):
    queryId: str
    intent: str   # summary | search | qa | action_items
    answer: str
