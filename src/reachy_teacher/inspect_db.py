from __future__ import annotations
import json
from sqlalchemy import select
from .db import init_db, SessionLocal, Lesson, Session

def main():
    init_db()
    with SessionLocal() as db:
        lesson = db.execute(select(Lesson).order_by(Lesson.created_at.desc())).scalars().first()
        sess = db.execute(select(Session).order_by(Session.started_at.desc())).scalars().first()

        print("LESSON:", lesson.id, "|", lesson.title)
        print("SESSION:", sess.id, "| student:", sess.student_id, "| segment_index:", sess.segment_index)
        print("SCORE:", sess.score, "/", sess.score_max)

        transcript = json.loads(sess.transcript_json)
        roles = [e.get("role") for e in transcript if isinstance(e, dict)]
        print("TRANSCRIPT EVENTS:", len(transcript))
        print("HAS quiz_agent:", "quiz_agent" in roles)
        print("HAS grader_agent:", "grader_agent" in roles)
        print("HAS summary_agent:", "summary_agent" in roles)

if __name__ == "__main__":
    main()
