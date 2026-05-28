"""Lightweight domain data models introduced by the v7.3 schema gate."""

from .evidence import EvidenceSpan
from .problem import ProblemClaim, QuestionNode
from .research import SearchQuery, SearchResult, IdentifiedMethod
from .method import MethodPlan
from .gate import GateIssue, GateResult
from .workflow import StepResult

__all__ = [
    "EvidenceSpan",
    "ProblemClaim",
    "QuestionNode",
    "SearchQuery",
    "SearchResult",
    "IdentifiedMethod",
    "MethodPlan",
    "GateIssue",
    "GateResult",
    "StepResult",
]
