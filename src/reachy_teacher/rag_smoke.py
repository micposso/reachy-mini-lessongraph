from __future__ import annotations

import os
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma


def main() -> None:
    # 1) Inputs
    pdf_path = Path("lessons/lesson1.pdf")
    if not pdf_path.exists():
        raise FileNotFoundError(f"Missing PDF: {pdf_path.resolve()}")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in this terminal session.")

    persist_dir = Path("./chroma_index")
    collection = "lesson_pdfs"

    # 2) Load PDF (page-per-document)
    docs = PyPDFLoader(str(pdf_path)).load()

    # 3) Split into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = splitter.split_documents(docs)

    # add stable chunk ids for citations
    for i, d in enumerate(chunks):
        d.metadata["chunk_id"] = f"{pdf_path.stem}_chunk_{i}"

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
