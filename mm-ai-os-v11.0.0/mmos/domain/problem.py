from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProblemClaim:
    claim_type: str
    evidence_ids: list[str]
    claim: str = ""
    text: str = ""
    confidence: float = 0.0


@dataclass(frozen=True)
class QuestionNode:
    question_id: str
    title: str = ""
    goal: dict = field(default_factory=dict)
    domain_family: dict = field(default_factory=dict)
    task_archetypes: list[dict] = field(default_factory=list)
    variables: list[dict] = field(default_factory=list)
    constraints: list[dict] = field(default_factory=list)
    required_outputs: list[dict] = field(default_factory=list)
    source_evidence_ids: list[str] = field(default_factory=list)
