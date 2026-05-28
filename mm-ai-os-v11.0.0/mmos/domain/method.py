from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class MethodPlan:
    question_id: str
    primary_model: dict | None = None
    alternative_models: list[dict] = field(default_factory=list)
    optimization_method: dict | None = None
    verification_approach: dict | None = None
    literature_references: list[dict] = field(default_factory=list)
    citation_count: int = 0
    method_count: int = 0
