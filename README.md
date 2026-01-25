reachy-mini-lessongraph is a LangGraph-orchestrated, multi agent tutoring pipeline for Reachy Mini. It ingests lesson PDFs, builds a retrieval index (RAG), generates structured 15 minute lesson plans, runs an interactive teaching session through the Reachy Mini SDK (speech, movement, and expressive behaviors), administers a five question quiz, grades responses against grounded rubrics, and emails a session summary while persisting progress for lesson continuation.

If you want a more provocative positioning for your audience: call it a “robotic learning OS” and explicitly state it is built around durable orchestration and stateful sessions rather than chat prompts, which is one of LangGraph’s core reasons to exist.

# Getting Started

## Activate Environment in CMD

.venv\Scripts\activate.bat

## Running the Daemon

The Reachy Mini daemon must be running to communicate with the robot. Start it in a separate terminal:

```bash
uv run reachy-mini-daemon
```

Local Dashboard runs on http://localhost:8000/

For simulation mode:

```bash
uv run reachy-mini-daemon --sim
```

## Running the RAG smoke test

```bash
  uv run --env-file .env python -m reachy_teacher.rag_smoke
```

## Running the Teaching Graph

Execute the main teaching pipeline with:

```bash
  uv run --env-file .env python -m reachy_teacher.teach_graph
```

Set a new student

```bash
  set STUDENT_ID=alice_2024
```

List students

```bash
  python -m reachy_teacher.db
```

This will:
1. Ingest lesson PDFs and build a RAG retrieval index
2. Generate a structured 15-minute lesson plan
3. Run an interactive teaching session through Reachy Mini (speech, movement, expressive behaviors)
4. Administer a five-question quiz
5. Grade responses against grounded rubrics
6. Email a session summary and persist progress for lesson continuation