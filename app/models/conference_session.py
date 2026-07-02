from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

ParticipantKind = Literal["acs_user", "phone"]

@dataclass(slots=True)
class ConferenceSession:
    """통화 세션 상태를 저장하는 인메모리 도메인 엔티티"""
    id: str
    call_connection_id: str | None = None
    server_call_id: str | None = None
    correlation_id: str | None = None
    state: str = "created"
    participants: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)