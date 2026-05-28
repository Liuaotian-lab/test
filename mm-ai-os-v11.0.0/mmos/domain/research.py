from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SearchQuery:
    query_id: str
    query: str
    purpose: str
    evidence_ids: list[str] = field(default_factory=list)
    priority: float = 0.5
    required: bool = False


@dataclass(frozen=True)
class IdentifiedMethod:
    method_name: str
    role: str
    relevance_score: float = 0.0
    evidence_span: str = ""
    source_title: str = ""
    source_url: str = ""


@dataclass(frozen=True)
class SearchResult:
    source_id: str
    title: str
    query_id: str
    snippet: str = ""
    url: str = ""
    doi: str = ""
    identified_methods: list[dict] = field(default_factory=list)
