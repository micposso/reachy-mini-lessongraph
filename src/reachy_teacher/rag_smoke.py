from __future__ import annotations

import os
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from .document_loader import load_documents, select_course_interactive


def main() -> None:
    # 1) Let user select a course
    course = select_course_interactive("lessons")
    if not course:
        print("No course selected. Exiting.")
        return

    lesson_files = course.lesson_files

    print(f"\nLoading {len(lesson_files)} lesson file(s) from '{course.display_name}':")
    for f in lesson_files:
        print(f"  - {f.name}")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in this terminal session.")

    persist_dir = Path("./chroma_index")
    collection = "lesson_docs"  # renamed from lesson_pdfs to reflect multi-format support

    # 2) Load all lesson documents (PDF and Markdown)
    docs = load_documents(lesson_files)

    # 3) Split into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = splitter.split_documents(docs)

    # add stable chunk ids for citations
    for i, d in enumerate(chunks):
        source = Path(d.metadata.get("source", "unknown"))
        d.metadata["chunk_id"] = f"{source.stem}_chunk_{i}"

    # 4) Vector store
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=api_key)
    vs = Chroma(
        collection_name=collection,
        persist_directory=str(persist_dir),
        embedding_function=embeddings,
    )

    # Only ingest if empty (avoid duplicating on repeated runs)
    if vs._collection.count() == 0:
        vs.add_documents(chunks)
        print(f"Ingested {len(chunks)} chunks into {persist_dir.resolve()}")
    else:
        print(f"Using existing index at {persist_dir.resolve()} (count={vs._collection.count()})")

    # 5) Retrieval sanity check
    retriever = vs.as_retriever(search_kwargs={"k": 5})
    query = "Summarize the main concept and give 3 key points."
    results = retriever.invoke(query)

    print("\n--- TOP RESULTS ---\n")
    for r in results:
        cid = r.metadata.get("chunk_id", "no_chunk_id")
        page = r.metadata.get("page", "n/a")
        print(f"[{cid}] page={page}")
        print(r.page_content[:500].replace("\n", " ").strip())
        print()

if __name__ == "__main__":
    main()
