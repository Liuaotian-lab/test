"""
Plan Builder — v7.0

Builds an executable method plan from matched methods and search results.
Every plan entry MUST cite at least one search result as its evidence source.
No self-knowledge fallback permitted.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import read_json, write_json
from mmos.core.artifacts import read_official_json, write_official_json
from mmos.kernel.events import now_iso


def build_method_plan(
    case_dir: Path,
    question_id: str | None = None,
    strict: bool = True,
) -> dict[str, Any]:
    """
    Build a structured, source-backed method plan for each question.

    The method plan builds a dynamic,
    search-evidence-backed plan. Each entry includes:
    - primary_model: main mathematical approach with source citation
    - alternative_models: backup approaches
    - optimization_method: how to solve/optimize
    - verification_approach: how to independently verify
    - literature_references: all cited search results

    Args:
        case_dir: Case directory.
        question_id: Single question or all.
        strict: If True, uncited methods cause failure.

    Returns:
        {
            "status": "passed" | "failed",
            "plans": { "Q1": { "primary_model": {...}, ... }, ... },
        }
    """
    case_dir = Path(case_dir).resolve()

    # Load method matches
    matches_data = read_official_json(case_dir, "workspace/academic_search/method_matches.json", {}) or {}
    if not matches_data.get("matches"):
        return _fail("NO_METHOD_MATCHES", "Run method-match first.", strict)

    # Load search results for citation linking
    search_data = read_official_json(case_dir, "workspace/academic_search/search_results.json", {}) or {}

    plans = {}
    plan_dir = case_dir / "workspace" / "method_plan"
    plan_dir.mkdir(parents=True, exist_ok=True)

    for qid, match in matches_data.get("matches", {}).items():
        q_plan = _build_one_plan(qid, match, search_data)
        plans[qid] = q_plan
        write_official_json(case_dir, f"workspace/method_plan/{qid}_method_plan.json", q_plan)

    # Validate all plans have citations
    uncited = _find_uncited(plans)
    if strict and uncited:
        raise RuntimeError(
            f"Uncited method claims found in plans: {uncited}. "
            f"Every method claim MUST reference a search result."
        )

    out = {
        "status": "passed" if not uncited else "warning",
        "case_id": case_dir.name,
        "timestamp": now_iso(),
        "plans": plans,
        "uncited_claims": uncited,
    }
    write_official_json(case_dir, "workspace/method_plan/case.method_plan_summary.json", out)
    return out


def _build_one_plan(qid: str, match: dict, search_data: dict) -> dict:
    """Build a single question's method plan from matched methods."""
    methods = match.get("methods", [])
    # Separate methods by role
    model_methods = [m for m in methods if m.get("role") in ("model", "primary_model", None)]
    opt_methods = [m for m in methods if m.get("role") == "optimization"]
    verif_methods = [m for m in methods if m.get("role") == "verification"]

    primary = model_methods[0] if model_methods else None
    alternatives = model_methods[1:4] if len(model_methods) > 1 else []

    # Build reference list from all methods
    refs = []
    seen = set()
    for m in methods:
        src = m.get("source_title") or m.get("source_url", "")
        if src and src not in seen:
            seen.add(src)
            refs.append({
                "title": m.get("source_title", "Unknown"),
                "url": m.get("source_url", ""),
                "snippet": m.get("source_snippet", ""),
                "relevance": m.get("relevance_score", 0),
            })

    return {
        "question_id": qid,
        "primary_model": primary,
        "alternative_models": alternatives,
        "optimization_method": opt_methods[0] if opt_methods else None,
        "verification_approach": verif_methods[0] if verif_methods else None,
        "literature_references": refs,
        "citation_count": len(refs),
        "method_count": len(methods),
    }


def _find_uncited(plans: dict) -> list[str]:
    """Find any method claims that lack citations."""
    uncited = []
    for qid, plan in plans.items():
        if plan.get("primary_model") and not plan.get("literature_references"):
            uncited.append(f"{qid}.primary_model")
        if plan.get("citation_count", 0) == 0:
            uncited.append(f"{qid}.all_methods")
    return uncited


def _fail(code: str, message: str, strict: bool) -> dict:
    result = {"status": "failed", "code": code, "message": message}
    if strict:
        raise RuntimeError(f"[{code}] {message}")
    return result
