from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class GateIssue:
    severity: str
    code: str
    message: str
    path: str = ""


@dataclass(frozen=True)
class GateResult:
    gate: str
    status: str
    blocking_issues: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)
    next_action: str = ""
