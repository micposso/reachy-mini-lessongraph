from __future__ import annotations

import json
import os
from typing import List

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from ..state import QuizQuestion


class QuizOut(BaseModel):
    questions: List[QuizQuestion] = Field(..., min_length=5, max_length=5)


SYSTEM = """You are a quiz agent.
Create EXACTLY 5 questions about the lesson that was just taught.

Hard rules:
- Use ONLY the provided lesson plan + transcript + retrieved passages.
- Each question MUST include:
  - ideal_answer
  - 3 to 5 rubric_points
  - sources: list of chunk_id strings from retrieved passages
- Return ONLY valid JSON matching the schema. No markdown. No extra keys.
"""


def generate_quiz(lesson_title: str, transcript: list[dict], retrieved: list[dict]) -> list[QuizQuestion]:
    api_key = os.environ["OPENAI_API_KEY"]
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    llm = ChatOpenAI(model=model, api_key=api_key, temperature=0.2)

    schema = json.dumps(QuizOut.model_json_schema(), indent=2)

    payload = {
        "lesson_title": lesson_title,
        "transcript": transcript,
        "retrieved": retrieved,
        "schema": schema,
    }

    resp = llm.invoke(
        [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(payload, indent=2)},
        ]
    )

    # ChatOpenAI returns an AIMessage; use .content for the text. :contentReference[oaicite:1]{index=1}
    out = QuizOut.model_validate_json(resp.content)
    return out.questions
