"""
app/services/agent_service.py - 회의 코파일럿의 'AI 두뇌' (Azure OpenAI function calling).

사용자 질문/요약/회의록 요청을 받아, 회의 자막을 조회하는 툴을 gpt에게 주고
gpt가 스스로 툴을 호출 → DB 결과로 답변/요약/회의록을 만든다.

routes_agent.py 가 answer_question / generate_and_save_summary / generate_minutes 를 호출한다.
"""

import json

from openai import AzureOpenAI

from app.config import settings
from app.repositories import agent_repository as repository

# .env 변수명이 AZURE_AI_* 든 AZURE_OPENAI_* 든, 값이 채워진 쪽을 쓴다.
_endpoint = settings.AZURE_AI_PROJECT_ENDPOINT or settings.AZURE_OPENAI_ENDPOINT
_api_key = settings.AZURE_AI_API_KEY or settings.AZURE_OPENAI_API_KEY
_deployment = settings.AZURE_AI_DEPLOYMENT or settings.AZURE_OPENAI_DEPLOYMENT or "gpt-5"
_base = _endpoint.split("/api/")[0].rstrip("/") if _endpoint else ""

# 애저 OpenAI 클라이언트 (키 인증)
client = AzureOpenAI(
    azure_endpoint=_base,
    api_key=_api_key,
    api_version=settings.AZURE_OPENAI_API_VERSION,
)


# AI가 부를 수 있는 '툴 목록' = repository 함수들의 설명서
TOOLS = [
    {"type": "function", "function": {
        "name": "get_transcripts",
        "description": "이 회의의 전체 자막(누가 무슨 말을 했는지)을 가져온다",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "get_participants",
        "description": "이 회의의 참가자 목록을 가져온다",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "search_transcripts",
        "description": "이 회의 자막에서 특정 키워드가 들어간 발언만 골라서 검색한다. "
                       "특정 주제(예: 예산, 일정)를 찾을 때 전체 자막을 다 받는 것보다 효율적이다.",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "찾을 키워드 (예: 예산, 일정, 디자인)"},
            },
            "required": ["keyword"],
        },
    }},
    {"type": "function", "function": {
        "name": "get_summary_snapshot",
        "description": "이 회의에 대해 이미 저장돼 있는 최신 요약을 가져온다. "
                       "아직 저장된 요약이 없으면 비어있다고 알려준다.",
        "parameters": {"type": "object", "properties": {}},
    }},
]


def _run_tool(db, meeting_id, name, args=None):
    """AI가 부른 툴 이름(+인자)에 맞춰 실제 repository 함수를 실행한다."""
    args = args or {}
    if name == "get_transcripts":
        rows = repository.get_transcripts(db, meeting_id)
        return [{"speaker": r.speaker, "content": r.cleaned_text or r.original_text} for r in rows]
    if name == "get_participants":
        return [nm for _id, nm in repository.get_participants(db, meeting_id)]
    if name == "search_transcripts":
        rows = repository.search_transcripts(db, meeting_id, keyword=args.get("keyword"))
        return [{"speaker": r.speaker, "content": r.cleaned_text or r.original_text} for r in rows]
    if name == "get_summary_snapshot":
        snap = repository.get_summary_snapshot(db, meeting_id)
        if snap is None:
            return {"summary": None, "note": "아직 저장된 요약이 없습니다"}
        return {"summary": snap.summary_json, "version": snap.version,
                "coverage_to_seq": snap.coverage_to_seq}
    return {"error": f"unknown tool: {name}"}


# 언어 코드 → 사람이 읽는 이름. 시스템 프롬프트에 박아서 '그 언어로만' 답하게 만든다.
_LANG_NAMES = {
    "ko": "한국어", "en": "English", "ja": "日本語", "zh": "中文",
    "ko-KR": "한국어", "en-US": "English", "ja-JP": "日本語", "zh-CN": "中文",
}


def answer_question(db, meeting_id, message, response_language="ko"):
    """
    사용자 질문(message)에 대해, 이 회의(meeting_id)의 데이터를 활용해
    gpt가 만든 답변 텍스트를 돌려준다.
    """
    lang_name = _LANG_NAMES.get(response_language, response_language)
    system_prompt = (
        f"너는 이 회의의 코파일럿이다. "
        f"[할 수 있는 것] 제공된 도구로 이 회의의 자막 조회·키워드 검색, 참가자 조회, 저장된 요약 조회를 하고, "
        f"그 내용을 바탕으로 요약·설명·번역·질문 답변을 '텍스트로' 작성한다. "
        f"[할 수 없는 것] 파일 저장·내보내기(PDF·Word·텍스트), 이메일·드라이브·폴더 등 외부 전송·저장, "
        f"자막·요약·회의 데이터의 수정·삭제, 회의 제어(음소거·종료·참가자 추가), 알림·예약, 이 회의 밖의 정보 조회. "
        f"이런 요청은 실행할 수 있는 척하거나 '해드릴까요?'라고 제안하지 말고, "
        f"'그 기능은 이 채팅에서는 실행할 수 없어요.'라고 분명히 답한 뒤, 대안이 있으면 안내한다"
        f"(회의록 파일은 화면의 '회의록 다운로드' 기능을 사용하도록). "
        f"자막·요약에 근거 없는 내용은 지어내지 않는다. 모르면 모른다고 한다. "
        f"최종 답변은 반드시 '{lang_name}'(으)로만 작성한다. 사용자가 다른 언어로 물어도 '{lang_name}'로 유지한다."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
    ]

    while True:
        resp = client.chat.completions.create(model=_deployment, messages=messages, tools=TOOLS)
        msg = resp.choices[0].message

        if msg.tool_calls:                # AI가 "이 툴 불러줘" 하면
            messages.append(msg)
            for tc in msg.tool_calls:
                try:
                    tool_args = json.loads(tc.function.arguments or "{}")
                except (json.JSONDecodeError, TypeError):
                    tool_args = {}
                result = _run_tool(db, meeting_id, tc.function.name, tool_args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })
        else:                             # 더 부를 툴 없으면 = 최종 답변
            return msg.content


# 요약 생성용 지시문. gpt에게 자막을 주고 '정해진 JSON 구조'로만 요약을 뽑게 한다.
_SUMMARY_SYSTEM = (
    "너는 회의록 요약 전문가다. 주어진 회의 자막을 읽고 아래 JSON 구조로만 답한다"
    "(설명 문장 없이 JSON만 출력):\n"
    '{\n'
    '  "keyDiscussions": ["핵심 논의 요점", ...],\n'
    '  "decisions": [{"item": "안건", "decision": "결정 내용", "decidedBy": "결정한 사람"}],\n'
    '  "actionItems": [{"assignee": "담당자", "task": "할 일"}],\n'
    '  "pendingTopics": ["아직 결론 안 난 주제", ...]\n'
    '}\n'
    "자막에 근거가 없는 항목은 빈 배열로 둔다. 없는 내용을 지어내지 않는다."
)


# 증분 갱신용 지시문. '기존 요약 + 그 이후 새 자막'을 주고 갱신된 요약을 같은 구조로 뽑는다.
_SUMMARY_UPDATE_SYSTEM = (
    "너는 회의록 요약 전문가다. '기존 요약(JSON)'과 그 이후 새로 도착한 자막이 주어진다. "
    "둘을 합쳐 '갱신된 요약'을 아래 JSON 구조로만 출력한다(설명 문장 없이 JSON만):\n"
    '{\n'
    '  "keyDiscussions": ["핵심 논의 요점", ...],\n'
    '  "decisions": [{"item": "안건", "decision": "결정 내용", "decidedBy": "결정한 사람"}],\n'
    '  "actionItems": [{"assignee": "담당자", "task": "할 일"}],\n'
    '  "pendingTopics": ["아직 결론 안 난 주제", ...]\n'
    '}\n'
    "규칙: 기존 요약의 항목은 새 자막과 모순되지 않는 한 유지·보완한다. "
    "새 자막에서 결론이 난 보류 주제는 decisions/actionItems로 옮기고 pendingTopics에서 뺀다. "
    "자막에 근거 없는 내용은 지어내지 않는다."
)


def generate_and_save_summary(db, meeting_id, response_language="ko", prev_snap=None):
    """
    요약을 생성해 스냅샷으로 저장한다.

    - prev_snap=None : 전체 자막으로 처음부터 요약 (최초 생성 / refresh)
    - prev_snap 있음 : '기존 요약 + 그 이후 새 자막만' gpt에 줘서 갱신 (증분 → 토큰·시간 절약)

    반환: (스냅샷, 이번에 반영한 자막 수).
    새 자막이 없으면 (prev_snap, 0), 자막 자체가 없으면 (None, 0).
    """
    after_id = prev_snap.coverage_to_seq if prev_snap else None
    rows = repository.get_transcripts(db, meeting_id, after_id=after_id)
    if not rows:
        return prev_snap, 0

    lang_name = _LANG_NAMES.get(response_language, response_language)
    transcript_text = "\n".join(f"{r.speaker or '화자'}: {r.cleaned_text or r.original_text}" for r in rows)

    if prev_snap is not None:   # 증분: 기존 요약 + 새 자막만
        system_text = _SUMMARY_UPDATE_SYSTEM
        user_text = (
            f"[기존 요약]\n{json.dumps(prev_snap.summary_json, ensure_ascii=False)}\n\n"
            f"[새 자막]\n{transcript_text}"
        )
    else:                       # 최초/전체: 자막 전체
        system_text = _SUMMARY_SYSTEM
        user_text = transcript_text

    resp = client.chat.completions.create(
        model=_deployment,
        messages=[
            {"role": "system", "content": system_text + f" 모든 값은 '{lang_name}'로 쓴다."},
            {"role": "user", "content": user_text},
        ],
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content
    try:
        summary_json = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        summary_json = {"overview": content}

    coverage_to_seq = max(r.id for r in rows)   # 이번에 반영한 마지막 자막 id(워터마크)
    snap = repository.save_summary_snapshot(db, meeting_id, summary_json, coverage_to_seq)
    return snap, len(rows)


# 회의록 생성용 지시문. 자막+요약을 받아 '정식 회의록' 구조 JSON으로 뽑는다.
_MINUTES_SYSTEM = (
    "너는 회의록 작성 전문가다. 주어진 '지금까지의 요약(JSON)'과 그 이후 새 자막을 근거로 "
    "(요약이 없으면 자막 전체를 근거로) 정식 회의록을 아래 JSON 구조로만 작성한다(설명 없이 JSON만 출력):\n"
    '{\n'
    '  "title": "회의 제목(내용에서 추론)",\n'
    '  "keyDiscussions": ["핵심 논의 요점", ...],\n'
    '  "decisions": [{"item": "안건", "decision": "결정 내용", "decidedBy": "결정한 사람"}],\n'
    '  "actionItems": [{"assignee": "담당자", "task": "할 일", "due": "기한(없으면 빈 문자열)"}],\n'
    '  "pendingTopics": ["아직 결론 안 난 주제", ...]\n'
    '}\n'
    "자막에 근거 없는 내용은 지어내지 않는다. 빈 항목은 빈 배열로 둔다. "
    "title(제목)에는 '이번 분기'·'오늘'·'지난주' 같은 시점 표현을 넣지 말고 핵심 주제로 간결히 쓴다."
)


def generate_minutes(db, meeting_id, response_language="ko"):
    """
    회의록을 gpt로 생성해 dict로 돌려준다. 참석자 목록도 채워 넣는다.

    - 저장된 요약이 있으면: '요약 + 그 이후 새 자막만' 사용 (전체 자막을 다시 안 읽어 시간·토큰 절약)
    - 요약이 없으면: 전체 자막 사용 (기존 방식)
    - 요약도 자막도 없으면 None.
    """
    snap = repository.get_summary_snapshot(db, meeting_id)
    after_id = snap.coverage_to_seq if snap else None
    rows = repository.get_transcripts(db, meeting_id, after_id=after_id)  # 요약 이후 새 자막만(요약 없으면 전체)
    if snap is None and not rows:
        return None

    participants = [nm for _id, nm in repository.get_participants(db, meeting_id) if nm]
    summary_text = (
        json.dumps(snap.summary_json, ensure_ascii=False) if snap else "(저장된 요약 없음)"
    )
    transcript_text = (
        "\n".join(f"{r.speaker or '화자'}: {r.cleaned_text or r.original_text}" for r in rows)
        if rows else "(요약 이후 새 자막 없음)"
    )
    lang_name = _LANG_NAMES.get(response_language, response_language)

    resp = client.chat.completions.create(
        model=_deployment,
        messages=[
            {"role": "system", "content": _MINUTES_SYSTEM + f" 모든 값은 '{lang_name}'로 쓴다."},
            {"role": "user", "content":
                f"[참석자]\n{', '.join(participants)}\n\n"
                f"[지금까지의 요약]\n{summary_text}\n\n"
                f"[요약 이후 새 자막]\n{transcript_text}"},
        ],
        response_format={"type": "json_object"},
    )
    try:
        data = json.loads(resp.choices[0].message.content)
    except (json.JSONDecodeError, TypeError):
        data = {"title": "회의록", "keyDiscussions": [], "decisions": [],
                "actionItems": [], "pendingTopics": []}

    data["participants"] = participants
    return data
