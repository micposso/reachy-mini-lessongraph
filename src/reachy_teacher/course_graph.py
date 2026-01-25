"""Course graph that handles full course progression with multiple lessons."""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Literal

from sqlalchemy import select
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .agents.quiz_agent import generate_quiz
from .agents.grader_agent import grade_quiz, grade_single_answer
from .agents.summary_agent import generate_summary
from .agents.progression_agent import evaluate_progression

from .db import init_db, SessionLocal, Lesson, Session
from .document_loader import load_documents, select_course_interactive, Course
from .io.robot_factory import get_robot
from .state import LessonPlan, GraphState


PLANNER_SYSTEM = """You are a lesson planning agent.
Create a 15-minute lesson plan grounded ONLY in the retrieved passages.
Return ONLY valid JSON matching the provided schema.
Each segment MUST include sources with chunk_id values from retrieved passages.
"""


def make_retriever_for_lesson(lesson_path: str):
    """Create a retriever for a single lesson file."""
    api_key = os.environ["OPENAI_API_KEY"]
    persist_dir = os.getenv("CHROMA_DIR", "./chroma_index")
    # Use a unique collection per lesson to avoid mixing content
    collection = f"lesson_{Path(lesson_path).stem}"

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
        docs = load_documents([lesson_path])
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        chunks = splitter.split_documents(docs)
        for i, d in enumerate(chunks):
            source = Path(d.metadata.get("source", lesson_path))
            d.metadata["chunk_id"] = f"{source.stem}_chunk_{i}"
        vs.add_documents(chunks)

    return vs.as_retriever(search_kwargs={"k": 6})


def build_course_graph():
    """Build a graph that teaches an entire course with multiple lessons."""
    g = StateGraph(GraphState)

    # ==================== PLANNING NODES ====================

    def plan_current_lesson_node(state: GraphState) -> GraphState:
        """Plan the current lesson in the course."""
        lesson_index = state.get("current_lesson_index", 0)
        lesson_files = state.get("course_lesson_files", [])

        if lesson_index >= len(lesson_files):
            state["course_completed"] = True
            return state

        lesson_path = lesson_files[lesson_index]
        lesson_name = Path(lesson_path).stem

        print("\n" + "=" * 50)
        print(f"PLANNING LESSON {lesson_index + 1}/{len(lesson_files)}: {lesson_name}")
        print("=" * 50)

        # Create retriever for this lesson
        retriever = make_retriever_for_lesson(lesson_path)

        # Retrieve content
        query = f"Create a lesson plan about the content in this document"
        docs = retriever.invoke(query)

        state["retrieved"] = [
            {
                "text": d.page_content,
                "chunk_id": d.metadata.get("chunk_id"),
                "page": d.metadata.get("page"),
            }
            for d in docs
        ]

        # Generate lesson plan
        api_key = os.environ["OPENAI_API_KEY"]
        model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        llm = ChatOpenAI(model=model, api_key=api_key, temperature=0.2)

        lesson_id = str(uuid.uuid4())
        schema = json.dumps(LessonPlan.model_json_schema(), indent=2)

        resp = llm.invoke(
            [
                {"role": "system", "content": PLANNER_SYSTEM},
                {
                    "role": "user",
                    "content": f"lesson_id={lesson_id}\nTopic=Create a lesson from the retrieved content\n\nRetrieved:\n{json.dumps(state['retrieved'], indent=2)}\n\nSchema:\n{schema}",
                },
            ]
        )

        # Validate and store
        plan = LessonPlan.model_validate_json(resp.content)
        state["lesson_plan_json"] = resp.content
        state["lesson_id"] = plan.lesson_id

        # Save to DB
        with SessionLocal() as db:
            db.merge(
                Lesson(id=plan.lesson_id, title=plan.title, plan_json=resp.content)
            )
            db.commit()

        print(f"Planned: {plan.title}")
        return state

    # ==================== SESSION NODES ====================

    def ensure_session_node(state: GraphState) -> GraphState:
        """Ensure a session exists for this student and lesson."""
        plan = LessonPlan.model_validate_json(state["lesson_plan_json"])

        student_id = state.get("student_id")
        if not student_id:
            raise RuntimeError("student_id missing from graph input.")

        with SessionLocal() as db:
            sess = db.execute(
                select(Session).where(
                    Session.student_id == student_id,
                    Session.lesson_id == plan.lesson_id,
                )
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

        if state.get("attempt_number") is None:
            state["attempt_number"] = 1

        return state

    # ==================== TEACHING NODES ====================

    def introduce_node(state: GraphState) -> GraphState:
        """Reachy introduces the lesson."""
        plan = LessonPlan.model_validate_json(state["lesson_plan_json"])
        robot = state["robot"]
        lesson_index = state.get("current_lesson_index", 0)
        total_lessons = len(state.get("course_lesson_files", []))
        course_name = state.get("course_name", "this course")

        print("\n" + "=" * 50)
        print("INTRODUCTION")
        print("=" * 50)

        if lesson_index == 0:
            # First lesson in course
            robot.set_emotion("happy")
            robot.do_motion("nod")
            robot.say(f"Hello! I am Reachy, and I will be your teacher today.")
            robot.say(f"Welcome to {course_name}!")
            robot.say(f"This course has {total_lessons} lessons. Let's start with the first one.")
        else:
            # Continuing in course
            robot.set_emotion("excited")
            robot.do_motion("nod")
            robot.say(f"Great job on the previous lesson!")
            robot.say(f"Now let's continue with lesson {lesson_index + 1} of {total_lessons}.")

        robot.set_emotion("encouraging")
        robot.say(f"Today we will learn about {plan.title}.")
        robot.say("Let's begin!")

        return state

    def teach_segment_node(state: GraphState) -> GraphState:
        """Teach the next segment."""
        plan = LessonPlan.model_validate_json(state["lesson_plan_json"])
        i = state["segment_index"]

        if i >= len(plan.segments):
            state["done"] = True
            return state

        seg = plan.segments[i]
        robot = state["robot"]

        print(f"\nSEGMENT {i + 1}/{len(plan.segments)}: {seg.title}")

        robot.set_emotion(seg.emotion)
        robot.do_motion(seg.motion)
        robot.say(seg.script)

        # Ask check question
        ans = robot.ask_and_listen_text(seg.check_question, record_seconds=12.0).strip()
        if not ans:
            ans = input("[Fallback typing] > ").strip()

        robot.say(f"You said: {ans}")

        # Grade
        rating = grade_single_answer(
            question=seg.check_question,
            ideal_answer="",
            student_answer=ans,
            context=seg.script,
        )

        if rating == "correct":
            robot.set_emotion("excited")
            robot.do_motion("celebrate")
            robot.say("That is correct!")
        elif rating == "close":
            robot.set_emotion("encouraging")
            robot.say("Almost!")
        else:
            robot.set_emotion("encouraging")
            robot.say("Not quite, but let's continue.")

        state["transcript"].append({"role": "teacher", "text": seg.script})
        state["transcript"].append({"role": "student", "text": ans})
        state["segment_index"] = i + 1
        state["done"] = False

        return state

    # ==================== QUIZ NODES ====================

    def retrieve_quiz_context_node(state: GraphState) -> GraphState:
        """Retrieve context for quiz generation."""
        lesson_files = state.get("course_lesson_files", [])
        lesson_index = state.get("current_lesson_index", 0)

        if lesson_index < len(lesson_files):
            retriever = make_retriever_for_lesson(lesson_files[lesson_index])
            plan = LessonPlan.model_validate_json(state["lesson_plan_json"])
            docs = retriever.invoke(f"Key facts for quiz on: {plan.title}")

            state["retrieved"] = [
                {"text": d.page_content, "chunk_id": d.metadata.get("chunk_id")}
                for d in docs
            ]

        return state

    def quiz_node(state: GraphState) -> GraphState:
        """Conduct the quiz."""
        plan = LessonPlan.model_validate_json(state["lesson_plan_json"])
        robot = state["robot"]

        print("\nQUIZ TIME!")

        robot.say("Now let's do a short quiz.")

        questions = generate_quiz(plan.title, state["transcript"], state["retrieved"])
        state["quiz"] = [q.model_dump() for q in questions]
        state["student_answers"] = []

        for i, q in enumerate(state["quiz"], start=1):
            robot.say(f"Question {i}: {q['question']}")
            ans = robot.ask_and_listen_text("Your answer.", record_seconds=12.0).strip()
            if not ans:
                ans = input("[Fallback typing] > ").strip()

            state["student_answers"].append(ans)
            robot.say(f"You said: {ans}")

            rating = grade_single_answer(
                question=q["question"],
                ideal_answer=q.get("ideal_answer", ""),
                student_answer=ans,
            )

            if rating == "correct":
                robot.set_emotion("excited")
                robot.say("Correct!")
            elif rating == "close":
                robot.set_emotion("encouraging")
                robot.say("Almost!")
            else:
                robot.set_emotion("encouraging")
                robot.say("Not quite.")

            state["transcript"].append({"role": "quiz", "question": q["question"]})
            state["transcript"].append({"role": "student", "text": ans})

        return state

    def grade_node(state: GraphState) -> GraphState:
        """Grade the quiz."""
        robot = state["robot"]

        result = grade_quiz(state["quiz"], state["student_answers"], state["retrieved"])
        state["quiz_result"] = result.model_dump()
        state["score"] = result.total_score
        state["score_max"] = result.max_score

        score_pct = (state["score"] / state["score_max"] * 100) if state["score_max"] > 0 else 0

        print(f"Score: {state['score']}/{state['score_max']} ({score_pct:.0f}%)")

        robot.say(f"You scored {state['score']} out of {state['score_max']}.")

        return state

    def progression_node(state: GraphState) -> GraphState:
        """Evaluate if student should repeat or advance."""
        plan = LessonPlan.model_validate_json(state["lesson_plan_json"])
        robot = state["robot"]

        progression = evaluate_progression(
            score=state["score"],
            score_max=state["score_max"],
            passing_threshold=60.0,
            quiz_questions=state.get("quiz"),
            student_answers=state.get("student_answers"),
            quiz_result=state.get("quiz_result"),
            lesson_title=plan.title,
        )

        state["progression_decision"] = progression.model_dump()

        print(f"Decision: {progression.decision.upper()}")

        if progression.decision == "advance":
            robot.set_emotion("excited")
            robot.do_motion("dance")
            robot.say(f"Congratulations! You passed with {progression.score_percentage:.0f} percent!")
        else:
            robot.set_emotion("encouraging")
            robot.do_motion("encourage")
            robot.say(f"You scored {progression.score_percentage:.0f} percent.")
            robot.say("Let's review this lesson one more time.")

        state["transcript"].append({
            "role": "progression",
            "decision": progression.decision,
        })

        return state

    # ==================== REPEAT NODES ====================

    def reset_for_repeat_node(state: GraphState) -> GraphState:
        """Reset state for repeating the lesson."""
        state["attempt_number"] = state.get("attempt_number", 1) + 1
        state["segment_index"] = 0
        state["quiz"] = []
        state["student_answers"] = []
        state["quiz_result"] = None
        state["score"] = None
        state["score_max"] = None
        state["done"] = False

        print(f"\nRESETTING FOR ATTEMPT #{state['attempt_number']}")

        return state

    def re_introduce_node(state: GraphState) -> GraphState:
        """Re-introduce lesson for repeat attempt."""
        plan = LessonPlan.model_validate_json(state["lesson_plan_json"])
        robot = state["robot"]
        attempt = state.get("attempt_number", 2)

        robot.set_emotion("encouraging")
        robot.say(f"Let's try again! This is attempt {attempt}.")
        robot.say(f"We will review {plan.title} together.")
        robot.say("Here we go!")

        return state

    # ==================== COURSE PROGRESSION NODES ====================

    def advance_to_next_lesson_node(state: GraphState) -> GraphState:
        """Move to the next lesson in the course."""
        lesson_index = state.get("current_lesson_index", 0)
        lesson_files = state.get("course_lesson_files", [])

        next_index = lesson_index + 1

        if next_index >= len(lesson_files):
            state["course_completed"] = True
            print("\nCOURSE COMPLETED!")
        else:
            state["current_lesson_index"] = next_index
            # Reset lesson state for next lesson
            state["segment_index"] = 0
            state["done"] = False
            state["attempt_number"] = 1
            state["quiz"] = []
            state["student_answers"] = []
            state["quiz_result"] = None
            state["score"] = None
            state["score_max"] = None
            state["transcript"] = []
            print(f"\nADVANCING TO LESSON {next_index + 1}/{len(lesson_files)}")

        return state

    def course_complete_node(state: GraphState) -> GraphState:
        """Celebrate course completion."""
        robot = state["robot"]
        course_name = state.get("course_name", "the course")
        total_lessons = len(state.get("course_lesson_files", []))

        print("\n" + "=" * 50)
        print("COURSE COMPLETED!")
        print("=" * 50)

        robot.set_emotion("excited")
        robot.do_motion("dance")
        robot.say("Congratulations!")
        robot.say(f"You have completed all {total_lessons} lessons in {course_name}!")

        robot.set_emotion("happy")
        robot.say("You should be very proud of yourself!")
        robot.say("Keep learning and growing. See you next time!")

        robot.do_motion("dance")

        return state

    def persist_node(state: GraphState) -> GraphState:
        """Persist session state to DB."""
        with SessionLocal() as db:
            sess = db.get(Session, state.get("session_id"))
            if sess:
                sess.segment_index = state.get("segment_index", 0)
                sess.transcript_json = json.dumps(state.get("transcript", []))
                if state.get("score") is not None:
                    sess.score = state["score"]
                    sess.score_max = state.get("score_max")
                db.commit()
        return state

    # ==================== ROUTING FUNCTIONS ====================

    def route_after_teach(state: GraphState) -> Literal["teach", "quiz"]:
        if state.get("done"):
            return "quiz"
        return "teach"

    def route_after_progression(state: GraphState) -> Literal["advance", "repeat"]:
        decision = state.get("progression_decision", {})
        if decision.get("decision") == "repeat":
            return "repeat"
        return "advance"

    def route_after_advance(state: GraphState) -> Literal["next_lesson", "complete"]:
        if state.get("course_completed"):
            return "complete"
        return "next_lesson"

    # ==================== BUILD GRAPH ====================

    g.add_node("plan_lesson", plan_current_lesson_node)
    g.add_node("ensure_session", ensure_session_node)
    g.add_node("introduce", introduce_node)
    g.add_node("teach", teach_segment_node)
    g.add_node("retrieve_quiz_context", retrieve_quiz_context_node)
    g.add_node("quiz", quiz_node)
    g.add_node("grade", grade_node)
    g.add_node("progression", progression_node)
    g.add_node("persist", persist_node)
    g.add_node("reset_for_repeat", reset_for_repeat_node)
    g.add_node("re_introduce", re_introduce_node)
    g.add_node("advance_to_next", advance_to_next_lesson_node)
    g.add_node("course_complete", course_complete_node)

    # Entry: plan first lesson
    g.set_entry_point("plan_lesson")

    # Plan -> Session -> Introduce -> Teach
    g.add_edge("plan_lesson", "ensure_session")
    g.add_edge("ensure_session", "introduce")
    g.add_edge("introduce", "teach")

    # Teach loop
    g.add_conditional_edges("teach", route_after_teach, {"teach": "teach", "quiz": "retrieve_quiz_context"})

    # Quiz -> Grade -> Progression
    g.add_edge("retrieve_quiz_context", "quiz")
    g.add_edge("quiz", "grade")
    g.add_edge("grade", "progression")

    # Progression: advance or repeat
    g.add_conditional_edges(
        "progression",
        route_after_progression,
        {"advance": "persist", "repeat": "reset_for_repeat"},
    )

    # Repeat flow
    g.add_edge("reset_for_repeat", "re_introduce")
    g.add_edge("re_introduce", "teach")

    # After persist (only on advance): check for next lesson
    g.add_edge("persist", "advance_to_next")

    # After advance: either next lesson or complete
    g.add_conditional_edges(
        "advance_to_next",
        route_after_advance,
        {"next_lesson": "plan_lesson", "complete": "course_complete"},
    )

    # Course complete -> END
    g.add_edge("course_complete", END)

    return g.compile()


def main():
    """Run the course graph with interactive course selection."""
    init_db()

    # Select a course
    course = select_course_interactive("lessons")
    if not course:
        print("No course selected. Exiting.")
        return

    print(f"\nSelected course: {course.display_name}")
    print(f"Lessons: {course.lesson_count}")
    for i, f in enumerate(course.lesson_files, 1):
        print(f"  {i}. {f.name}")

    # Get student ID
    student_id = os.getenv("STUDENT_ID")
    if not student_id:
        student_id = f"student_{uuid.uuid4().hex[:8]}"
        print(f"\nGenerated student ID: {student_id}")

    # Get robot
    robot = get_robot()
    print(f"\nUsing robot: {type(robot).__name__}")

    # Build and run graph
    app = build_course_graph()

    try:
        if hasattr(robot, "open"):
            robot.open()

        result = app.invoke({
            "student_id": student_id,
            "robot": robot,
            "course_name": course.display_name,
            "course_lesson_files": [str(f) for f in course.lesson_files],
            "current_lesson_index": 0,
        })

        print("\n" + "=" * 50)
        print("SESSION COMPLETE")
        print("=" * 50)
        print(f"Course: {course.display_name}")
        print(f"Completed: {result.get('course_completed', False)}")
        print(f"Final lesson index: {result.get('current_lesson_index', 0) + 1}/{course.lesson_count}")

    finally:
        if hasattr(robot, "close"):
            robot.close()


if __name__ == "__main__":
    main()
