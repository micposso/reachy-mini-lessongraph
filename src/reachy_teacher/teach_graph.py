from __future__ import annotations

import json
import uuid
from typing import Literal

from sqlalchemy import select
from langgraph.graph import StateGraph, END

from .db import init_db, SessionLocal, Lesson, Session
from .state import LessonPlan, GraphState
from .io.robot_mock import RobotMock


def build_teach_graph():
    g = StateGraph(GraphState)

    def load_lesson_node(state: GraphState) -> GraphState:
        lesson_id = state.get("lesson_id")
        with SessionLocal() as db:
            if lesson_id:
                row = db.get(Lesson, lesson_id)
            else:
                row = db.execute(select(Lesson).order_by(Lesson.created_at.desc())).scalars().first()
            if not row:
                raise RuntimeError("No lesson found in DB. Run planner_only_graph first.")
        state["lesson_plan_json"] = row.plan_json
        state["lesson_id"] = row.id
        return state

    def ensure_session_node(state: GraphState) -> GraphState:
        plan = LessonPlan.model_validate_json(state["lesson_plan_json"])
        student_id = state.get("student_id")
        if not student_id:
            raise RuntimeError("student_id missing from graph input. Call app.invoke({'student_id': ...}).")

        with SessionLocal() as db:
            sess = db.execute(
                select(Session).where(Session.student_id == student_id, Session.lesson_id == plan.lesson_id)
            ).scalars().first()

            if not sess:
                sess = Session(
                    id=str(uuid.uuid4()),
                    student_id=student_id,
                    lesson_id=plan.lesson_id,
                    segment_index=0,
                    transcript_json="[]",
                )
                db.add(sess)
                db.commit()
                db.refresh(sess)

            state["session_id"] = sess.id
            state["segment_index"] = sess.segment_index
            state["transcript"] = json.loads(sess.transcript_json)

        return state

    def teach_next_segment_node(state: GraphState) -> GraphState:
        plan = LessonPlan.model_validate_json(state["lesson_plan_json"])
        i = state["segment_index"]

        if i >= len(plan.segments):
            state["done"] = True
            return state

        seg = plan.segments[i]
        robot = RobotMock()

        robot.set_emotion(seg.emotion)
        robot.do_motion(seg.motion)
        robot.say(seg.script)

        ans = input(f"[Student] {seg.check_question}\n> ").strip()

        state["transcript"].append({"role": "teacher", "text": seg.script, "sources": seg.sources})
        state["transcript"].append({"role": "student", "text": ans})
        state["segment_index"] = i + 1
        state["done"] = False
        return state

    def persist_node(state: GraphState) -> GraphState:
        with SessionLocal() as db:
            sess = db.get(Session, state["session_id"])
            if not sess:
                raise RuntimeError("Session missing in DB.")
            sess.segment_index = state["segment_index"]
            sess.transcript_json = json.dumps(state["transcript"])
            db.commit()
        return state

    def route(state: GraphState) -> Literal["teach", "end"]:
        return "end" if state.get("done") else "teach"

    g.add_node("load_lesson", load_lesson_node)
    g.add_node("ensure_session", ensure_session_node)
    g.add_node("teach", teach_next_segment_node)
    g.add_node("persist", persist_node)

    g.set_entry_point("load_lesson")
    g.add_edge("load_lesson", "ensure_session")
    g.add_edge("ensure_session", "teach")
    g.add_edge("teach", "persist")
    g.add_conditional_edges("persist", route, {"teach": "teach", "end": END})

    return g.compile()


def main():
    init_db()
    app = build_teach_graph()
    out = app.invoke({
        "student_id": "student_001",
        # optional: "lesson_id": "faf4de07-1b99-4b36-bb88-db12d772639b"
    })
    print("\nDONE:", out.get("done"), "segment_index:", out.get("segment_index"))

if __name__ == "__main__":
    main()
