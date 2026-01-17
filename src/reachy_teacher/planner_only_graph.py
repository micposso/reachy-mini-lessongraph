from __future__ import annotations
import os, json, uuid
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .state import GraphState, LessonPlan

def make_retriever(pdf_paths: list[str]):
    api_key = os.environ["OPENAI_API_KEY"]
    persist_dir = "./chroma_index"
    collection = "lesson_pdfs"

    embeddings = OpenAIEmbeddings(model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-large"), api_key=api_key)
    vs = Chroma(collection_name=collection, persist_directory=persist_dir, embedding_function=embeddings)

    if vs._collection.count() == 0:
        docs = []
        for p in pdf_paths:
            docs.extend(PyPDFLoader(p).load())
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        chunks = splitter.split_documents(docs)
        for i, d in enumerate(chunks):
            d.metadata["chunk_id"] = f"{os.path.basename(pdf_paths[0])}_chunk_{i}"
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
        retriever = make_retriever(state["pdf_paths"])
        q = f"Create a 15-minute beginner lesson plan about: {state['topic']}"
        docs = retriever.invoke(q)
        state["retrieved"] = [
            {"text": d.page_content, "chunk_id": d.metadata.get("chunk_id"), "page": d.metadata.get("page")}
            for d in docs
        ]
        return state

    def plan_node(state: GraphState) -> GraphState:
        api_key = os.environ["OPENAI_API_KEY"]
        model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        llm = ChatOpenAI(model=model, api_key=api_key, temperature=0.2)

        lesson_id = str(uuid.uuid4())
        schema = json.dumps(LessonPlan.model_json_schema(), indent=2)

        resp = llm.invoke([
            {"role": "system", "content": PLANNER_SYSTEM},
            {"role": "user", "content": f"lesson_id={lesson_id}\nTopic={state['topic']}\n\nRetrieved:\n{json.dumps(state['retrieved'], indent=2)}\n\nSchema:\n{schema}"}
        ])

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
    graph = build_graph()
    out = graph.invoke({
        "pdf_paths": ["lessons/lesson1.pdf"],
        "topic": "Use the PDF content to decide the topic"
    })
    print(out["lesson_plan_json"])

if __name__ == "__main__":
    main()
