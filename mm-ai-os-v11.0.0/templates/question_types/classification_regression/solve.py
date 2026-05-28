from __future__ import annotations
from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def solve(stage: str, budget: str, context: dict) -> dict:
    """Generic placeholder solver.

    The template intentionally returns `exploratory` quality. A real question-specific
    solver should replace this implementation.
    """
    return {
        "question_id": context.get("question_id", "__QUESTION__"),
        "status": "success",
        "stage": stage,
        "method": "template_placeholder_solver",
        "quality_level": "exploratory",
        "created_at": now_iso(),
        "objective_value": None,
        "diagnostics": {
            "fallback_used": False,
            "budget": budget,
            "warnings": ["Template solver; replace with a real model before final submission."]
        }
    }
