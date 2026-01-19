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
from .agents.summary_agent import generate_summary

from .db import init_db, SessionLocal, Lesson, Session
from .io.robot_factory import get_robot
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

    def introduce_node(state: GraphState) -> GraphState:
        """Reachy introduces itself and the lesson topic."""
        plan = LessonPlan.model_validate_json(state["lesson_plan_json"])
        robot = state["robot"]

        print("\n" + "="*50)
        print("👋 INTRODUCTION")
        print("="*50)

        # Reachy introduces itself
        robot.set_emotion("happy")
        robot.do_motion("nod")
        robot.say(f"Hello! I am Reachy, and I will be your teacher today.")

        robot.set_emotion("excited")
        robot.say(f"We are going to learn about {plan.title}.")

        robot.set_emotion("encouraging")
        robot.say("I will teach you in several segments, and then we will have a short quiz to test what you learned.")

        robot.say("Let's begin!")

        return state

    def teach_next_segment_node(state: GraphState) -> GraphState:
        plan = LessonPlan.model_validate_json(state["lesson_plan_json"])
        i = state["segment_index"]

        if i >= len(plan.segments):
            print("\n" + "="*50)
            print("✅ ALL SEGMENTS COMPLETE - Moving to quiz")
            print("="*50)
            state["done"] = True
            return state

        seg = plan.segments[i]
        robot = state["robot"]

        print("\n" + "="*50)
        print(f"📚 SEGMENT {i+1}/{len(plan.segments)}: {seg.title}")
        print(f"   Emotion: {seg.emotion} | Motion: {seg.motion}")
        print("="*50)

        # Speak the lesson segment with emotion + motion first
        robot.set_emotion(seg.emotion)
        robot.do_motion(seg.motion)
        robot.say(seg.script)

        # Ask the segment check question, listen for answer (fallback to typing)
        ans = robot.ask_and_listen_text(seg.check_question, record_seconds=12.0).strip()
        if not ans:
            print("⌨️  [No speech detected - fallback to typing]")
            ans = input("[Fallback typing] > ").strip()

        # Repeat the answer and give encouraging feedback
        robot.set_emotion("happy")
        robot.say(f"You said: {ans}")
        robot.set_emotion("encouraging")
        robot.do_motion("nod")
        robot.say("Great! Let's continue to the next part of our lesson.")

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
        robot = state["robot"]

        print("\n" + "="*50)
        print("📝 QUIZ TIME!")
        print("="*50)

        robot.say("Now we will do a short quiz. Answer five questions.")

        print("🔄 Generating quiz questions...")
        questions = generate_quiz(plan.title, state["transcript"], state["retrieved"])
        state["quiz"] = [q.model_dump() for q in questions]
        state["student_answers"] = []
        print(f"✅ Generated {len(questions)} questions")

        for i, q in enumerate(state["quiz"], start=1):
            print(f"\n--- Question {i}/{len(state['quiz'])} ---")
            robot.say(f"Question {i}: {q['question']}")
            ans = robot.ask_and_listen_text("Your answer.", record_seconds=12.0).strip()
            if not ans:
                print("⌨️  [No speech detected - fallback to typing]")
                ans = input("[Fallback typing] > ").strip()

            state["student_answers"].append(ans)

            # Repeat the answer
            robot.say(f"You said: {ans}")

            # Check if answer is correct (simple keyword matching against ideal answer)
            ideal = q.get("ideal_answer", "").lower()
            ans_lower = ans.lower()
            # Consider correct if key words from ideal answer appear in student's answer
            ideal_words = set(ideal.split())
            ans_words = set(ans_lower.split())
            overlap = len(ideal_words & ans_words)
            is_correct = overlap >= max(1, len(ideal_words) // 2)  # At least half the key words

            if is_correct:
                robot.set_emotion("excited")
                robot.say("Woohoo! That is correct!")
                robot.do_motion("celebrate")
                robot.say("Great job! Let's move to the next question.")
            else:
                robot.set_emotion("encouraging")
                robot.do_motion("shake")
                robot.say("Oops, not quite, but let's continue to the next question.")

            # Persist quiz events in transcript (no DB schema changes)
            state["transcript"].append(
                {"role": "quiz_agent", "question": q["question"], "sources": q.get("sources", [])}
            )
            state["transcript"].append({"role": "student", "text": ans})

        return state

    def grade_node(state: GraphState) -> GraphState:
        print("\n" + "="*50)
        print("📊 GRADING QUIZ...")
        print("="*50)

        result = grade_quiz(state["quiz"], state["student_answers"], state["retrieved"])
        state["quiz_result"] = result.model_dump()

        state["score"] = state["quiz_result"]["total_score"]
        state["score_max"] = state["quiz_result"]["max_score"]

        print(f"✅ Score: {state['score']}/{state['score_max']}")

        state["transcript"].append({"role": "grader_agent", "result": state["quiz_result"]})
        return state

    def summarize_node(state: GraphState) -> GraphState:
        print("\n" + "="*50)
        print("📋 GENERATING LESSON SUMMARY...")
        print("="*50)

        plan = LessonPlan.model_validate_json(state["lesson_plan_json"])

        summary = generate_summary(
            lesson_id=plan.lesson_id,
            lesson_title=plan.title,
            student_id=state["student_id"],
            session_id=state["session_id"],
            transcript=state["transcript"],
            quiz_result=state.get("quiz_result"),
            score=state.get("score"),
            score_max=state.get("score_max"),
        )

        state["lesson_summary"] = summary.model_dump()
        state["transcript"].append({"role": "summary_agent", "summary": state["lesson_summary"]})

        print("✅ Summary generated")
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
        if not state.get("done"):
            return "teach"
        if state.get("score") is not None:
            return "end"
        return "quiz"

    g.add_node("load_lesson", load_lesson_node)
    g.add_node("ensure_session", ensure_session_node)
    g.add_node("introduce", introduce_node)
    g.add_node("teach", teach_next_segment_node)
    g.add_node("retrieve_quiz_context", retrieve_quiz_context_node)
    g.add_node("quiz", quiz_node)
    g.add_node("grade", grade_node)
    g.add_node("summarize", summarize_node)
    g.add_node("persist", persist_node)

    g.set_entry_point("load_lesson")
    g.add_edge("load_lesson", "ensure_session")
    g.add_edge("ensure_session", "introduce")
    g.add_edge("introduce", "teach")
    g.add_edge("teach", "persist")

    g.add_conditional_edges("persist", route, {"teach": "teach", "quiz": "retrieve_quiz_context", "end": END})

    g.add_edge("retrieve_quiz_context", "quiz")
    g.add_edge("quiz", "grade")
    g.add_edge("grade", "summarize")
    g.add_edge("summarize", "persist")

    return g.compile()


def main():
    init_db()
    app = build_teach_graph()

    robot = get_robot()
    print("\n" + "="*50)
    print(f"🚀 STARTING LESSON with {type(robot).__name__}")
    print("="*50)

    try:
        # If Reachy adapter supports open(), reserve audio devices now to fail fast
        if hasattr(robot, "open"):
            print("🔌 Opening robot connection...")
            robot.open()
            print("✅ Robot ready")

        out = app.invoke(
            {
                "student_id": "student_reachy_011",
                "robot": robot,
            }
        )
    finally:
        try:
            if hasattr(robot, "close"):
                robot.close()
        except Exception:
            pass

    print("\nDONE:", out.get("done"), "segment_index:", out.get("segment_index"))
    if out.get("score") is not None:
        print(f"FINAL SCORE: {out['score']}/{out.get('score_max')}")


if __name__ == "__main__":
    main()
