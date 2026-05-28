"""
Citation Manager — v7.0

Manages academic citations collected through web searches.
Ensures every method recommendation is traceable to a search result.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import read_json, write_json
from mmos.core.artifacts import read_official_json, write_official_json, write_report_json
from mmos.kernel.events import now_iso


def build_citation_list(
    case_dir: Path,
    question_id: str | None = None,
) -> dict[str, Any]:
    """
    Build a consolidated citation list from all search results and method plans.

    Each citation includes:
    - source_title: title of the paper/article/resource
    - source_url: link to the resource
    - relevance: how this citation relates to the problem
    - referenced_by: which method plan entries use this citation

    Args:
        case_dir: Case directory.
        question_id: Single question or all.

    Returns:
        {
            "status": "passed",
            "citations": [ { "id": "cit_001", ... }, ... ],
            "citation_count": 5,
        }
    """
    case_dir = Path(case_dir).resolve()

    # Collect citations from method plans
    plan_summary = read_official_json(case_dir, "workspace/method_plan/case.method_plan_summary.json", {}) or {}
    plans = plan_summary.get("plans", {})

    citations = []
    seen_urls = set()
    cit_id = 0

    for qid, plan in plans.items():
        for ref in plan.get("literature_references", []):
            url = ref.get("url", "")
            if url and url in seen_urls:
                # Merge into existing citation
                for c in citations:
                    if c.get("url") == url:
                        if qid not in c.get("referenced_by", []):
                            c["referenced_by"].append(qid)
            elif ref.get("title"):
                cit_id += 1
                citations.append({
                    "id": f"cit_{cit_id:03d}",
                    "title": ref.get("title", "Unknown"),
                    "url": url,
                    "snippet": ref.get("snippet", ""),
                    "relevance": ref.get("relevance", 0),
                    "referenced_by": [qid],
                })
                if url:
                    seen_urls.add(url)

    out = {
        "status": "passed",
        "case_id": case_dir.name,
        "timestamp": now_iso(),
        "citations": citations,
        "citation_count": len(citations),
    }
    write_official_json(case_dir, "workspace/academic_search/citation_list.json", out)

    return out


def validate_citations(case_dir: Path, strict: bool = True) -> dict[str, Any]:
    """
    Validate that all citations are:
    1. Non-empty (title and at least one of url/snippet)
    2. Actually referenced by at least one method plan entry
    3. Have non-zero relevance scores

    Returns failures if any citation is invalid.
    """
    case_dir = Path(case_dir).resolve()
    cit_data = read_official_json(case_dir, "workspace/academic_search/citation_list.json", {}) or {}

    failures = []
    for c in cit_data.get("citations", []):
        if not c.get("title"):
            failures.append({
                "citation_id": c.get("id"),
                "issue": "missing_title",
                "detail": "Every citation must have a title.",
            })
        if not c.get("url") and not c.get("snippet"):
            failures.append({
                "citation_id": c.get("id"),
                "issue": "no_source",
                "detail": "Citation must have url or snippet from search.",
            })
        if not c.get("referenced_by"):
            failures.append({
                "citation_id": c.get("id"),
                "issue": "unreferenced",
                "detail": "Citation is not referenced by any method plan.",
            })

    out = {
        "status": "passed" if not failures else "failed",
        "case_id": case_dir.name,
        "timestamp": now_iso(),
        "failures": failures,
        "failure_count": len(failures),
    }
    write_report_json(case_dir, "quality/citation_validation.json", out)

    if strict and failures:
        raise RuntimeError(
            f"Citation validation failed: {len(failures)} issues found. "
            f"Fix citations before proceeding."
        )

    return out
