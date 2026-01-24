from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from pydantic import BaseModel
from langchain_openai import ChatOpenAI

from ..state import QuizResult


REALTIME_SYSTEM = """You are a teaching assistant evaluating a student's answer in real-time.

Given a question, the ideal answer (or lesson context), and the student's response, determine how correct the answer is.

Return ONE of these three ratings:
- "correct" - The answer demonstrates clear understanding of the key concept (doesn't need to be word-for-word, synonyms and paraphrasing are fine)
- "close" - The answer shows partial understanding or is on the right track but missing key details
- "wrong" - The answer is incorrect, irrelevant, or the student said "I don't know"

Respond with ONLY a JSON object: {"rating": "correct"} or {"rating": "close"} or {"rating": "wrong"}
No explanation. No markdown. Just the JSON.
"""


def grade_single_answer(question: str, ideal_answer: str, student_answer: str, context: str = "") -> str:
    """
    Grade a single answer in real-time using LLM.
    Returns "correct", "close", or "wrong".

    Args:
        question: The question that was asked
        ideal_answer: The expected/ideal answer (can be empty if context is provided)
        student_answer: The student's response
        context: Optional lesson content to help determine correctness
    """
    api_key = os.environ["OPENAI_API_KEY"]
    # Use a fast model for real-time grading
    model = os.getenv("OPENAI_REALTIME_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    llm = ChatOpenAI(model=model, api_key=api_key, temperature=0.0)

    if context and not ideal_answer:
        prompt = f"""Lesson Content (what was just taught):
{context}

Question asked to student: {question}

Student's Answer: {student_answer}

Based on the lesson content, rate the student's answer."""
    else:
        prompt = f"""Question: {question}

Ideal Answer: {ideal_answer}

Student's Answer: {student_answer}

Rate the student's answer."""

    try:
        resp = llm.invoke(
            [
                {"role": "system", "content": REALTIME_SYSTEM},
                {"role": "user", "content": prompt},
            ]
        )
        result = json.loads(resp.content)
        rating = result.get("rating", "wrong")
        if rating not in ("correct", "close", "wrong"):
            rating = "wrong"
        return rating
    except Exception as e:
        print(f"⚠️ Real-time grading error: {e}")
        # Fallback: be generous
        return "close"


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
