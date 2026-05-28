"""
Method Matcher — v7.0

Matches academic search results to applicable mathematical methods.
Does NOT use hardcoded method lists. Every method recommendation MUST be
backed by at least one search result. No fallback to AI self-knowledge.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import read_json, write_json
from mmos.core.artifacts import read_official_json, write_official_json
from mmos.kernel.events import now_iso


def match_methods(
    case_dir: Path,
    question_id: str | None = None,
    strict: bool = True,
) -> dict[str, Any]:
    """
    Match search results to applicable methods for each question.

    The Agent must:
    1. Read each search result (title, snippet, URL)
    2. Identify candidate mathematical methods mentioned
    3. Assess applicability (relevance, feasibility, evidence level)
    4. Output a structured method match report

    Args:
        case_dir: Case directory.
        question_id: Single question or all.
        strict: If True, any question without matched methods fails.

    Returns:
        {
            "status": "passed" | "failed",
            "matches": { "Q1": { "methods": [...], "source_count": 5 }, ... },
        }

    Raises:
        RuntimeError: If strict=True and any question has zero matched methods.
    """
    case_dir = Path(case_dir).resolve()

    # Load search results
    search_data = read_official_json(case_dir, "workspace/academic_search/search_results.json", {}) or {}
    if not search_data.get("searches"):
        return _fail_strict("NO_SEARCH_RESULTS", "Run academic-search first.", strict)

    # Load signatures for context
    signatures = read_official_json(case_dir, "workspace/problem_signatures/case.signatures.json", {}) or {}

    matches = {}
    total_matched = 0
    for search in search_data.get("searches", []):
        qid = search["question_id"]
        signature = signatures.get("questions", {}).get(qid, {})
        q_matches = _match_one(search, signature)
        matches[qid] = q_matches
        if q_matches.get("method_count", 0) > 0:
            total_matched += 1

    # Write output
    out = {
        "status": "passed" if total_matched == len(matches) else "failed",
        "case_id": case_dir.name,
        "timestamp": now_iso(),
        "matches": matches,
        "question_count": len(matches),
        "matched_count": total_matched,
    }
    write_official_json(case_dir, "workspace/academic_search/method_matches.json", out)

    if strict and total_matched < len(matches):
        missing = [q for q, m in matches.items() if m.get("method_count", 0) == 0]
        raise RuntimeError(
            f"No methods matched for questions: {missing}. "
            f"Each method requirement MUST be backed by search results. "
            f"No fallback to AI self-knowledge is permitted."
        )

    return out


def _match_one(search: dict, signature: dict) -> dict:
    """
    Match one question's search results to methods.

    Returns a structured report that the Agent populates by:
    1. Reading each search result
    2. Extracting method names, descriptions, and source references
    3. Scoring each method on relevance, feasibility, evidence
    """
    results = search.get("results", [])
    queries = search.get("queries", [])
    method_candidates = []

    # For each search result, the Agent identifies candidate methods
    for i, result in enumerate(results):
        if not isinstance(result, dict):
            continue
        methods_from_result = result.get("identified_methods", [])
        for m in methods_from_result:
            m["source_result_index"] = i
            m["source_query"] = queries[i].get("query", "") if i < len(queries) else ""
            method_candidates.append(m)

    needs_extraction = bool(results) and not method_candidates
    extraction_tasks = []
    if needs_extraction:
        for i, result in enumerate(results):
            extraction_tasks.append({
                "result_index": i,
                "source_id": result.get("source_id") or f"SRC-{search.get('question_id','Q')}-{i+1:04d}",
                "query_id": result.get("query_id") or (queries[i].get("query_id") if i < len(queries) else None),
                "title": result.get("title", ""),
                "url": result.get("url") or result.get("doi") or result.get("identifier"),
                "required_action": "Populate identified_methods with method_name, role, evidence_span and relevance_score.",
            })
    return {
        "question_id": search.get("question_id"),
        "query_count": search.get("total_queries", 0),
        "result_count": len(results),
        "method_count": len(method_candidates),
        "methods": method_candidates,
        "needs_agent_extraction": needs_extraction,
        "method_extraction_tasks": extraction_tasks,
        "signature_summary": {
            "domain": (signature.get("domain_family") or {}).get("primary", "unknown"),
            "tasks": [t.get("task") for t in signature.get("task_archetypes", [])],
        },
        "note": "Agent must inspect search results and populate identified_methods before method-plan synthesis."
        if needs_extraction or not results else "",
    }


def _fail_strict(code: str, message: str, strict: bool) -> dict:
    result = {"status": "failed", "code": code, "message": message}
    if strict:
        raise RuntimeError(f"[{code}] {message}")
    return result
