from __future__ import annotations

import json
import os
import uuid
from typing import Literal

from sqlalchemy import select
from langgraph.graph import StateGraph, END
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from .agents.quiz_agent import generate_quiz
from .agents.grader_agent import grade_quiz
from .db import init_db, SessionLocal, Lesson, Session
from .io.robot_mock import RobotMock
from .state import LessonPlan, GraphState


def get_retriever():
    api_key = os.environ["OPENAI_API_KEY"]
    persist_dir = os.getenv("CHROMA_DIR", "./chroma_index")
    collection = "lesson_pdfs"

    embeddings = OpenAIEmbeddings(
        model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-large"),
        api_key=api_key,
    )

    vs = Chroma(
        collection_name=collection,
        persist_directory=persist_dir,
        embedding_function=embeddings,
    )

    # Chroma loads automatically from persist_directory.
    if vs._collection.count() == 0:
        raise RuntimeError(
            "Chroma index is empty. Run rag_smoke first to ingest PDFs (or ingest inside this flow)."
        )

    return vs.as_retriever(search_kwargs={"k": 6})


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
                    score=None,
                    score_max=None,
                )
                db.add(sess)
                db.commit()
                db.refresh(sess)

            state["session_id"] = sess.id
            state["segment_index"] = sess.segment_index
            state["transcript"] = json.loads(sess.transcript_json)
            state["score"] = sess.score
            state["score_max"] = sess.score_max

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

    def retrieve_quiz_context_node(state: GraphState) -> GraphState:
        plan = LessonPlan.model_validate_json(state["lesson_plan_json"])
        retriever = get_retriever()

        query = f"Key facts, definitions, and examples for a quiz on: {plan.title}"
        docs = retriever.invoke(query)

        state["retrieved"] = [
            {"text": d.page_content, "chunk_id": d.metadata.get("chunk_id"), "page": d.metadata.get("page")}
            for d in docs
        ]
        return state

    def quiz_node(state: GraphState) -> GraphState:
        plan = LessonPlan.model_validate_json(state["lesson_plan_json"])
        robot = RobotMock()

        robot.say("Now we will do a short quiz. Answer five questions.")

        questions = generate_quiz(plan.title, state["transcript"], state["retrieved"])
        state["quiz"] = [q.model_dump() for q in questions]
        state["student_answers"] = []

        for i, q in enumerate(state["quiz"], start=1):
            robot.say(f"Question {i}: {q['question']}")
            ans = input("> ").strip()
            state["student_answers"].append(ans)

            # Persist quiz in transcript without changing DB schema
            state["transcript"].append(
                {"role": "quiz_agent", "question": q["question"], "sources": q.get("sources", [])}
            )
            state["transcript"].append({"role": "student", "text": ans})

        return state

    def grade_node(state: GraphState) -> GraphState:
        result = grade_quiz(state["quiz"], state["student_answers"], state["retrieved"])
        state["quiz_result"] = result.model_dump()

        state["score"] = state["quiz_result"]["total_score"]
        state["score_max"] = state["quiz_result"]["max_score"]

        # Persist grading summary in transcript
        state["transcript"].append({"role": "grader_agent", "result": state["quiz_result"]})

        return state

    def persist_node(state: GraphState) -> GraphState:
        with SessionLocal() as db:
            sess = db.get(Session, state["session_id"])
            if not sess:
                raise RuntimeError("Session missing in DB.")

            sess.segment_index = state["segment_index"]
            sess.transcript_json = json.dumps(state["transcript"])

            if state.get("score") is not None:
                sess.score = state["score"]
                sess.score_max = state.get("score_max")

            db.commit()

        return state

    def route(state: GraphState) -> Literal["teach", "quiz", "end"]:
        # Keep teaching until done
        if not state.get("done"):
            return "teach"

        # Teaching done. If already graded, stop.
        if state.get("score") is not None:
            return "end"

        # Teaching done but not graded yet -> quiz
        return "quiz"

    g.add_node("load_lesson", load_lesson_node)
    g.add_node("ensure_session", ensure_session_node)
    g.add_node("teach", teach_next_segment_node)
    g.add_node("retrieve_quiz_context", retrieve_quiz_context_node)
    g.add_node("quiz", quiz_node)
    g.add_node("grade", grade_node)
    g.add_node("persist", persist_node)

    g.set_entry_point("load_lesson")
    g.add_edge("load_lesson", "ensure_session")
    g.add_edge("ensure_session", "teach")
    g.add_edge("teach", "persist")

    # Persist loops teaching, then branches to quiz, then grades, then persists once more, then ends.
    g.add_conditional_edges("persist", route, {"teach": "teach", "quiz": "retrieve_quiz_context", "end": END})

    g.add_edge("retrieve_quiz_context", "quiz")
    g.add_edge("quiz", "grade")
    g.add_edge("grade", "persist")

    return g.compile()


def main():
    init_db()
    app = build_teach_graph()
    out = app.invoke(
        {
            "student_id": "student_001",
            # optional: "lesson_id": "faf4de07-1b99-4b36-bb88-db12d772639b"
        }
    )

    print("\nDONE:", out.get("done"), "segment_index:", out.get("segment_index"))
    if out.get("score") is not None:
        print(f"FINAL SCORE: {out['score']}/{out.get('score_max')}")


if __name__ == "__main__":
    main()
