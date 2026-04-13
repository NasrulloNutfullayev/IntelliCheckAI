from __future__ import annotations

from typing import Any

from ai import evaluate_answer


def evaluate_with_ai(
    answer: str,
    question_text: str,
    reference_answer: str,
    rubric: dict[str, Any],
) -> dict[str, Any]:
    """Bridge between FastAPI endpoints and the semantic evaluation module."""
    return evaluate_answer(
        answer=answer,
        question_text=question_text,
        reference_answer=reference_answer,
        rubric=rubric,
    )
