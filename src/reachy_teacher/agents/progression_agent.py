"""Progression agent that evaluates student performance and decides next steps."""
from __future__ import annotations

import json
import os
from typing import List, Optional

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI


class ProgressionDecision(BaseModel):
    """Decision about whether a student should repeat or advance."""

    decision: str = Field(
        description="Either 'repeat' or 'advance'"
    )
    score_percentage: float = Field(
        description="The student's score as a percentage (0-100)"
    )
    passing_threshold: float = Field(
        description="The threshold percentage required to pass"
    )
    reasoning: str = Field(
        description="Brief explanation of the decision"
    )
    weak_areas: List[str] = Field(
        default_factory=list,
        description="Topics or concepts the student struggled with (if any)"
    )
    strong_areas: List[str] = Field(
        default_factory=list,
        description="Topics or concepts the student understood well (if any)"
    )
    recommendation: str = Field(
        description="Specific recommendation for the student's next steps"
    )


class ProgressionAnalysis(BaseModel):
    """LLM analysis of student performance (without decision)."""

    weak_areas: List[str] = Field(
        default_factory=list,
        description="Topics or concepts the student struggled with"
    )
    strong_areas: List[str] = Field(
        default_factory=list,
        description="Topics or concepts the student understood well"
    )
    reasoning: str = Field(
        description="Brief analysis of the student's performance"
    )
    recommendation: str = Field(
        description="Specific recommendation for the student's next steps"
    )


SYSTEM = """You are a learning performance analyzer.

Analyze the student's quiz performance and provide:
1. weak_areas: Topics/concepts the student struggled with (based on wrong answers)
2. strong_areas: Topics/concepts the student understood well (based on correct answers)
3. reasoning: Brief analysis of their performance
4. recommendation: Helpful next steps for the student

IMPORTANT: Do NOT decide if the student should repeat or advance - that decision is made separately based on the score threshold.

Hard rules:
- Return ONLY valid JSON matching the schema.
- No markdown. No extra keys.
- Be encouraging and constructive.
- Focus on growth mindset.
"""


def evaluate_progression(
    *,
    score: int,
    score_max: int,
    passing_threshold: float = 60.0,
    quiz_questions: Optional[List[dict]] = None,
    student_answers: Optional[List[str]] = None,
    quiz_result: Optional[dict] = None,
    lesson_title: str = "",
) -> ProgressionDecision:
    """
    Evaluate student performance and decide if they should repeat or advance.

    The decision (repeat/advance) is made deterministically based on score.
    The LLM only provides analysis of weak/strong areas and recommendations.

    Args:
        score: Student's total score
        score_max: Maximum possible score
        passing_threshold: Minimum percentage to pass (default 60%)
        quiz_questions: List of quiz questions with ideal answers
        student_answers: List of student's answers
        quiz_result: Detailed quiz grading result
        lesson_title: Title of the lesson for context

    Returns:
        ProgressionDecision with the decision and analysis
    """
    # DETERMINISTIC decision based on score - not LLM
    score_percentage = (score / score_max * 100) if score_max > 0 else 0
    decision = "advance" if score_percentage >= passing_threshold else "repeat"

    # Use LLM only for analysis
    api_key = os.environ["OPENAI_API_KEY"]
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    llm = ChatOpenAI(model=model, api_key=api_key, temperature=0.2)

    schema = json.dumps(ProgressionAnalysis.model_json_schema(), indent=2)

    payload = {
        "lesson_title": lesson_title,
        "score": score,
        "score_max": score_max,
        "score_percentage": round(score_percentage, 1),
        "decision": decision,  # inform LLM of the decision for context
        "quiz_questions": quiz_questions or [],
        "student_answers": student_answers or [],
        "quiz_result": quiz_result,
        "schema": schema,
    }

    resp = llm.invoke(
        [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(payload, indent=2)},
        ]
    )

    analysis = ProgressionAnalysis.model_validate_json(resp.content)

    # Combine deterministic decision with LLM analysis
    return ProgressionDecision(
        decision=decision,
        score_percentage=round(score_percentage, 1),
        passing_threshold=passing_threshold,
        reasoning=analysis.reasoning,
        weak_areas=analysis.weak_areas,
        strong_areas=analysis.strong_areas,
        recommendation=analysis.recommendation,
    )


def simple_progression_check(
    score: int,
    score_max: int,
    passing_threshold: float = 60.0,
) -> tuple[str, float]:
    """
    Simple progression check without LLM (for quick decisions).

    Args:
        score: Student's total score
        score_max: Maximum possible score
        passing_threshold: Minimum percentage to pass (default 60%)

    Returns:
        Tuple of (decision, score_percentage)
        decision is either 'repeat' or 'advance'
    """
    score_percentage = (score / score_max * 100) if score_max > 0 else 0
    decision = "advance" if score_percentage >= passing_threshold else "repeat"
    return decision, score_percentage
