"""Smoke test for the progression agent."""
from __future__ import annotations

import os


def main() -> None:
    from .agents.progression_agent import (
        evaluate_progression,
        simple_progression_check,
        ProgressionDecision,
    )

    print("=" * 60)
    print("PROGRESSION AGENT SMOKE TEST")
    print("=" * 60)

    # Test cases: (score, score_max, expected_decision)
    test_cases = [
        # Passing cases (>= 60%)
        (10, 10, "advance"),  # 100%
        (8, 10, "advance"),   # 80%
        (6, 10, "advance"),   # 60% - exactly at threshold
        # Failing cases (< 60%)
        (5, 10, "repeat"),    # 50%
        (3, 10, "repeat"),    # 30%
        (0, 10, "repeat"),    # 0%
        # Edge cases
        (6, 10, "advance"),   # 60% boundary
        (59, 100, "repeat"),  # 59% just below
        (60, 100, "advance"), # 60% exactly
    ]

    print("\n--- Simple Progression Check (no LLM) ---\n")
    all_passed = True
    for score, score_max, expected in test_cases:
        decision, pct = simple_progression_check(score, score_max, 60.0)
        status = "PASS" if decision == expected else "FAIL"
        if decision != expected:
            all_passed = False
        print(f"{status} Score {score}/{score_max} ({pct:.1f}%) -> {decision.upper()} (expected: {expected})")

    if all_passed:
        print("\nPASS All simple checks passed!")
    else:
        print("\nFAIL Some simple checks failed!")
        return

    # Test with LLM (requires API key)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("\nWARNING:  OPENAI_API_KEY not set - skipping LLM tests")
        return

    print("\n--- Full Progression Evaluation (with LLM) ---\n")

    # Test case 1: Student fails (should repeat)
    print("Test 1: Student scores 3/10 (30%) - should REPEAT")
    print("-" * 40)

    quiz_questions = [
        {"question": "What is a variable?", "ideal_answer": "A named container for storing data"},
        {"question": "What is a function?", "ideal_answer": "A reusable block of code"},
        {"question": "What is a loop?", "ideal_answer": "Code that repeats multiple times"},
        {"question": "What is a string?", "ideal_answer": "A sequence of characters"},
        {"question": "What is an integer?", "ideal_answer": "A whole number"},
    ]

    student_answers_fail = [
        "I don't know",
        "Something in programming",
        "I'm not sure",
        "Text maybe?",
        "A number",
    ]

    quiz_result_fail = {
        "total_score": 3,
        "max_score": 10,
        "per_question": [
            {"question": "What is a variable?", "score": 0, "feedback": "Incorrect"},
            {"question": "What is a function?", "score": 1, "feedback": "Partial"},
            {"question": "What is a loop?", "score": 0, "feedback": "Incorrect"},
            {"question": "What is a string?", "score": 1, "feedback": "Partial"},
            {"question": "What is an integer?", "score": 1, "feedback": "Partial"},
        ],
    }

    result1 = evaluate_progression(
        score=3,
        score_max=10,
        passing_threshold=60.0,
        quiz_questions=quiz_questions,
        student_answers=student_answers_fail,
        quiz_result=quiz_result_fail,
        lesson_title="Introduction to Programming",
    )

    print(f"Decision: {result1.decision.upper()}")
    print(f"Score: {result1.score_percentage}%")
    print(f"Threshold: {result1.passing_threshold}%")
    print(f"Reasoning: {result1.reasoning}")
    print(f"Weak areas: {result1.weak_areas}")
    print(f"Strong areas: {result1.strong_areas}")
    print(f"Recommendation: {result1.recommendation}")

    if result1.decision == "repeat":
        print("\nPASS Test 1 PASSED - correctly decided to REPEAT")
    else:
        print("\nFAIL Test 1 FAILED - should have decided to REPEAT")

    # Test case 2: Student passes (should advance)
    print("\n" + "=" * 40)
    print("Test 2: Student scores 8/10 (80%) - should ADVANCE")
    print("-" * 40)

    student_answers_pass = [
        "A variable is a named storage location for data",
        "A function is a reusable piece of code that performs a task",
        "A loop repeats code multiple times",
        "A string is text or a sequence of characters",
        "An integer is a whole number without decimals",
    ]

    quiz_result_pass = {
        "total_score": 8,
        "max_score": 10,
        "per_question": [
            {"question": "What is a variable?", "score": 2, "feedback": "Correct"},
            {"question": "What is a function?", "score": 2, "feedback": "Correct"},
            {"question": "What is a loop?", "score": 2, "feedback": "Correct"},
            {"question": "What is a string?", "score": 1, "feedback": "Partial"},
            {"question": "What is an integer?", "score": 1, "feedback": "Partial"},
        ],
    }

    result2 = evaluate_progression(
        score=8,
        score_max=10,
        passing_threshold=60.0,
        quiz_questions=quiz_questions,
        student_answers=student_answers_pass,
        quiz_result=quiz_result_pass,
        lesson_title="Introduction to Programming",
    )

    print(f"Decision: {result2.decision.upper()}")
    print(f"Score: {result2.score_percentage}%")
    print(f"Threshold: {result2.passing_threshold}%")
    print(f"Reasoning: {result2.reasoning}")
    print(f"Weak areas: {result2.weak_areas}")
    print(f"Strong areas: {result2.strong_areas}")
    print(f"Recommendation: {result2.recommendation}")

    if result2.decision == "advance":
        print("\nPASS Test 2 PASSED - correctly decided to ADVANCE")
    else:
        print("\nFAIL Test 2 FAILED - should have decided to ADVANCE")

    # Summary
    print("\n" + "=" * 60)
    print("SMOKE TEST COMPLETE")
    print("=" * 60)

    test1_ok = result1.decision == "repeat"
    test2_ok = result2.decision == "advance"

    if test1_ok and test2_ok:
        print("PASS All tests passed!")
    else:
        print("FAIL Some tests failed!")
        if not test1_ok:
            print("   - Test 1 (fail case) did not return 'repeat'")
        if not test2_ok:
            print("   - Test 2 (pass case) did not return 'advance'")


if __name__ == "__main__":
    main()
