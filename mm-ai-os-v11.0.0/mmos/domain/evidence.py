from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvidenceSpan:
    evidence_id: str
    text: str
    source_file: str = ""
    question_id: str | None = None
    text_hash: str = ""
    start_offset: int | None = None
    end_offset: int | None = None
    metadata: dict = field(default_factory=dict)
