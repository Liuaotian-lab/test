from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

DEFAULT_BUDGET = {
    "max_context_files": 8,
    "max_tool_calls": 30,
    "max_search_queries": 20,
    "max_runtime_seconds": 600,
    "max_candidate_outputs": 10,
}

@dataclass
class BudgetUsage:
    context_files: int = 0
    tool_calls: int = 0
    search_queries: int = 0
    runtime_seconds: int = 0
    candidate_outputs: int = 0


def evaluate_budget(usage: dict[str, Any], budget: dict[str, Any] | None = None) -> dict[str, Any]:
    budget = {**DEFAULT_BUDGET, **(budget or {})}
    checks = []
    allowed = True
    for key, limit_key in [
        ("context_files", "max_context_files"),
        ("tool_calls", "max_tool_calls"),
        ("search_queries", "max_search_queries"),
        ("runtime_seconds", "max_runtime_seconds"),
        ("candidate_outputs", "max_candidate_outputs"),
    ]:
        value = int(usage.get(key, 0))
        limit = int(budget.get(limit_key, 0))
        ok = value <= limit
        allowed = allowed and ok
        checks.append({"metric": key, "value": value, "limit": limit, "ok": ok})
    return {"schema_version": "8.0.0", "allowed": allowed, "checks": checks, "budget": budget}
