from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from pydantic import BaseModel
from langchain_openai import ChatOpenAI

from ..state import QuizResult


SYSTEM = """You are a strict grader.

Scoring:
- Each question is scored 0, 1, or 2 points based on the rubric.
- Total max score = number_of_questions * 2

Return ONLY valid JSON matching the schema.
No markdown. No extra keys.
"""


class GradeOut(QuizResult):
    pass


def grade_quiz(questions: List[Dict[str, Any]], student_answers: List[str], retrieved: List[Dict[str, Any]]) -> GradeOut:
    api_key = os.environ["OPENAI_API_KEY"]
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    llm = ChatOpenAI(model=model, api_key=api_key, temperature=0.0)

    schema = json.dumps(GradeOut.model_json_schema(), indent=2)

    payload = {
        "questions": questions,
        "student_answers": student_answers,
        "retrieved": retrieved,
        "schema": schema,
    }

    resp = llm.invoke(
        [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(payload, indent=2)},
        ]
    )

    return GradeOut.model_validate_json(resp.content)
