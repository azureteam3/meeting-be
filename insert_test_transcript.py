"""
insert_test_transcript.py - [테스트용] 공유 DB(transcript_records)에 가짜 자막을 넣는다.

에이전트 요약/채팅을 '데이터 있는 상태'로 테스트하려고 쓴다.
같은 MEETING_ID로 다시 실행하면 먼저 지우고 새로 넣으므로 중복 안 쌓임.

실행:  venv/bin/python insert_test_transcript.py
삭제:  파일 맨 아래 주석(삭제만) 참고

⚠️ transcript_records는 자막팀 공유 표다. 반드시 아래 같은 '테스트용 meeting_id'만 쓸 것.
"""

from app.db.postgres import SessionLocal
from sqlalchemy import text

# 테스트할 회의 ID. 프론트에서 테스트하려면 프론트의 SESSION_ID와 같게 둔다.
MEETING_ID = "00000000-0000-0000-0000-000000000001"

# (화자, 화자ID, 발화내용, 회의시작 후 경과ms) — offset_ms 순서대로 정렬됨
ROWS = [
    ("김철수", "s1", "이번 분기 API 연동 일정을 정합시다.", 1000),
    ("박성민", "s2", "10월은 일정이 빠듯하니 12월로 미루는 게 좋겠어요.", 2000),
    ("김철수", "s1", "좋습니다. 그럼 10월 말 완료로 확정하죠.", 3000),
    ("이영희", "s3", "디자인 시안은 다음 주에 공유하겠습니다.", 4000),
    ("박성민", "s2", "예산이 3분기에 70% 초과될 리스크가 있어 검토가 필요합니다.", 5000),
]

db = SessionLocal()

# 1) 같은 테스트 회의 자막이 있으면 먼저 지운다 (중복 방지)
db.execute(text("DELETE FROM transcript_records WHERE meeting_id = :m"), {"m": MEETING_ID})

# 2) 새로 넣는다 (transcript_records 컬럼 전부 채움 — NOT NULL 안전하게)
for i, (speaker, sid, content, offset) in enumerate(ROWS, start=1):
    db.execute(
        text(
            """
            INSERT INTO transcript_records
              (segment_id, meeting_id, session_id, event_type, speaker, speaker_id,
               original_text, cleaned_text, translated_text, original_language, target_language,
               confidence, is_reliable, needs_review, status, offset_ms, duration_ms, created_at)
            VALUES
              (:seg, :m, 'sess-test', 'final', :sp, :sid, :txt, :txt, NULL, 'ko-KR', 'ko',
               0.95, true, false, 'final', :off, 1500, now())
            """
        ),
        {"seg": f"seg-{i}", "m": MEETING_ID, "sp": speaker, "sid": sid, "txt": content, "off": offset},
    )

db.commit()
print(f"완료: '{MEETING_ID}' 회의에 자막 {len(ROWS)}줄 넣음.")
print(f"→ 이제 테스트: GET http://localhost:8000/agent/sessions/{MEETING_ID}/summary")
print("→ 또는 프론트 AI 채팅에서 '회의 요약해줘'")
db.close()

# ── 삭제만 하고 싶으면(테스트 끝나고 정리): 위 INSERT 부분 주석 처리하고 아래만 남겨 실행 ──
# db = SessionLocal()
# db.execute(text("DELETE FROM transcript_records WHERE meeting_id = :m"), {"m": MEETING_ID})
# db.execute(text("DELETE FROM meeting_summary_snapshot WHERE meeting_id = :m"), {"m": MEETING_ID})
# db.commit(); db.close()
# print("테스트 데이터 삭제 완료")
