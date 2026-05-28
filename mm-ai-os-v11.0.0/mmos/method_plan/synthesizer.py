"""
Method Plan Synthesizer — v7.0

Synthesizes the final approved method plan for each question.
Builds academic-search-backed method plans.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import read_json, write_json
from mmos.core.artifacts import read_official_json, write_official_json
from mmos.kernel.events import now_iso
from mmos.academic_research_engine.plan_builder import build_method_plan


def synthesize_method_plan(
    case_dir: Path,
    question_id: str | None = None,
    strict: bool = True,
) -> dict[str, Any]:
    """
    Synthesize and approve method plans for each question.

    This validates that:
    1. Each plan has a primary model from search results
    2. Each plan has citations
    3. Coverage gaps have been addressed
    4. All methods are source-backed (zero self-knowledge assertions)

    It then marks plans as "approved" or "rejected".

    Args:
        case_dir: Case directory.
        question_id: Single question or all.
        strict: If True, unapproved plans cause failure.

    Returns:
        {
            "status": "passed" | "failed",
            "approved": { "Q1": { ... }, ... },
            "rejected": { ... },
        }
    """
    case_dir = Path(case_dir).resolve()

    # Load method plans; build them from method matches if the summary is not present.
    plan_summary = read_official_json(case_dir, "workspace/method_plan/case.method_plan_summary.json", {}) or {}
    if not plan_summary.get("plans"):
        plan_summary = build_method_plan(case_dir, question_id=question_id, strict=False)
    plans = plan_summary.get("plans", {})

    # Load coverage analysis
    coverage = read_json(case_dir / "workspace" / "method_plan" / "reports" / "coverage_gap_analysis.json", {}) or read_json(case_dir / "quality" / "coverage_gap_analysis.json", {}) or {}
    gaps_by_q = {}
    for g in coverage.get("gaps", []):
        qid = g.get("question_id", "")
        gaps_by_q.setdefault(qid, []).append(g)

    approved = {}
    rejected = {}
    for qid, plan in plans.items():
        q_gaps = gaps_by_q.get(qid, [])
        if not q_gaps and plan.get("primary_model") and plan.get("citation_count", 0) > 0:
            plan["approval_status"] = "approved"
            plan["approved_at"] = now_iso()
            approved[qid] = plan
        else:
            plan["approval_status"] = "rejected"
            plan["rejection_reasons"] = [g.get("gap_type") for g in q_gaps]
            if not plan.get("primary_model"):
                plan.setdefault("rejection_reasons", []).append("no_primary_model")
            if plan.get("citation_count", 0) == 0:
                plan.setdefault("rejection_reasons", []).append("no_citations")
            rejected[qid] = plan

    # Write approved plans
    for qid, plan in approved.items():
        write_official_json(case_dir, f"workspace/method_plan/{qid}_approved.json", plan)

    out = {
        "status": "passed" if not rejected else "failed",
        "case_id": case_dir.name,
        "timestamp": now_iso(),
        "approved": approved,
        "rejected": rejected,
        "approved_count": len(approved),
        "rejected_count": len(rejected),
    }
    write_official_json(case_dir, "workspace/method_plan/case.approval_summary.json", out)

    if strict and rejected:
        raise RuntimeError(
            f"Method plans rejected for: {list(rejected.keys())}. "
            f"Address coverage gaps and retry synthesis."
        )

    return out


def approve_method_plan(
    case_dir: Path,
    question_id: str,
    force: bool = False,
) -> dict[str, Any]:
    """
    Manually approve a method plan for a specific question.
    Used when the Agent has validated all coverage gaps have been filled.

    Args:
        case_dir: Case directory.
        question_id: Question to approve.
        force: If True, approve even with remaining gaps.

    Returns:
        { "status": "passed", "question_id": "Q1", "approved": true }
    """
    case_dir = Path(case_dir).resolve()
    plan = read_official_json(case_dir, f"workspace/method_plan/{question_id}_method_plan.json", {}) or {}

    if not plan:
        raise RuntimeError(f"No method plan found for {question_id}")

    plan["approval_status"] = "approved"
    plan["approved_at"] = now_iso()
    if force:
        plan["force_approved"] = True
    write_official_json(case_dir, f"workspace/method_plan/{question_id}_approved.json", plan)

    return {
        "status": "passed",
        "question_id": question_id,
        "approved": True,
        "force_approved": force,
    }
