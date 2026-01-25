from __future__ import annotations
import os, json, uuid
from pathlib import Path
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .state import GraphState, LessonPlan
from .db import init_db, SessionLocal, Lesson
from .document_loader import load_documents


def make_retriever(lesson_paths: list[str]):
    """Create a retriever from lesson documents (PDF and Markdown supported)."""
    api_key = os.environ["OPENAI_API_KEY"]
    persist_dir = "./chroma_index"
    collection = "lesson_docs"  # renamed from lesson_pdfs to reflect multi-format support

    embeddings = OpenAIEmbeddings(
        model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-large"), api_key=api_key
    )
    vs = Chroma(
        collection_name=collection,
        persist_directory=persist_dir,
        embedding_function=embeddings,
    )

    if vs._collection.count() == 0:
        docs = load_documents(lesson_paths)
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        chunks = splitter.split_documents(docs)
        for i, d in enumerate(chunks):
            source = Path(d.metadata.get("source", lesson_paths[0] if lesson_paths else "unknown"))
            d.metadata["chunk_id"] = f"{source.stem}_chunk_{i}"
        vs.add_documents(chunks)

    return vs.as_retriever(search_kwargs={"k": 6})


PLANNER_SYSTEM = """You are a lesson planning agent.
Create a 15-minute lesson plan grounded ONLY in the retrieved passages.
Return ONLY valid JSON matching the provided schema.
Each segment MUST include sources with chunk_id values from retrieved passages.
"""


def build_graph():
    g = StateGraph(GraphState)

    def retrieve_node(state: GraphState) -> GraphState:
        retriever = make_retriever(state["lesson_paths"])
        q = f"Create a 15-minute beginner lesson plan about: {state['topic']}"
        docs = retriever.invoke(q)
        state["retrieved"] = [
            {
                "text": d.page_content,
                "chunk_id": d.metadata.get("chunk_id"),
                "page": d.metadata.get("page"),
            }
            for d in docs
        ]
        return state

    def plan_node(state: GraphState) -> GraphState:
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
                    "content": f"lesson_id={lesson_id}\nTopic={state['topic']}\n\nRetrieved:\n{json.dumps(state['retrieved'], indent=2)}\n\nSchema:\n{schema}",
                },
            ]
        )

        # Validate now so failures are immediate
        LessonPlan.model_validate_json(resp.content)

        state["lesson_plan_json"] = resp.content
        return state

    g.add_node("retrieve", retrieve_node)
    g.add_node("plan", plan_node)
    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "plan")
    g.add_edge("plan", END)

    return g.compile()


def main():
    from .document_loader import select_course_interactive

    init_db()

    # Let user select a course
    course = select_course_interactive("lessons")
    if not course:
        print("No course selected. Exiting.")
        return

    print(f"\nLoading {course.lesson_count} lesson file(s) from '{course.display_name}':")
    for f in course.lesson_files:
        print(f"  - {f.name}")

    graph = build_graph()
    out = graph.invoke(
        {
            "lesson_paths": [str(f) for f in course.lesson_files],
            "topic": "Use the lesson content to decide the topic",
        }
    )
    plan = LessonPlan.model_validate_json(out["lesson_plan_json"])

    with SessionLocal() as db:
        db.merge(
            Lesson(
                id=plan.lesson_id, title=plan.title, plan_json=out["lesson_plan_json"]
            )
        )
        db.commit()

    print(f"Saved lesson: {plan.lesson_id} | {plan.title}")


if __name__ == "__main__":
    main()
