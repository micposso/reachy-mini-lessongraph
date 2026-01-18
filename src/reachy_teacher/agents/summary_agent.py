from __future__ import annotations

import json
import os

from pydantic import BaseModel
from langchain_openai import ChatOpenAI

from ..state import LessonSummary


SYSTEM = """You are a lesson summary agent.

Create a concise summary for the student based ONLY on:
- lesson plan
- session transcript
- quiz_result (if present)
- score fields (if present)

Hard rules:
- Return ONLY valid JSON matching the schema.
- No markdown. No extra keys.
- Keep takeaways concrete and actionable.
"""


class SummaryOut(LessonSummary):
    pass


def generate_summary(
    *,
    lesson_id: str,
    lesson_title: str,
    student_id: str,
    session_id: str,
    transcript: list[dict],
    quiz_result: dict | None,
    score: int | None,
    score_max: int | None,
) -> SummaryOut:
    api_key = os.environ["OPENAI_API_KEY"]
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    llm = ChatOpenAI(model=model, api_key=api_key, temperature=0.2)

    schema = json.dumps(SummaryOut.model_json_schema(), indent=2)

    payload = {
        "lesson_id": lesson_id,
        "lesson_title": lesson_title,
        "student_id": student_id,
        "session_id": session_id,
        "transcript": transcript,
        "quiz_result": quiz_result,
        "score": score,
        "score_max": score_max,
        "schema": schema,
    }

    resp = llm.invoke(
        [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(payload, indent=2)},
        ]
    )

    return SummaryOut.model_validate_json(resp.content)
