"""
Coverage Checker — v7.0

Checks whether the method plan adequately covers all problem requirements.
Identifies gaps that need additional academic search.
No self-knowledge gap-filling — gaps are reported as failures requiring more search.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import read_json, write_json
from mmos.core.artifacts import read_official_json, write_report_json
from mmos.kernel.events import now_iso


def check_coverage(
    case_dir: Path,
    question_id: str | None = None,
    strict: bool = True,
) -> dict[str, Any]:
    """
    Check whether the method plan covers all aspects of the problem.

    Coverage dimensions:
    1. Modeling coverage: each task archetype has a corresponding model
    2. Solution coverage: each model has a solver/optimization method
    3. Verification coverage: independent verification approach exists
    4. Data coverage: attachment data usage is addressed
    5. Constraint coverage: all constraints have handling methods

    Args:
        case_dir: Case directory.
        question_id: Single question or all.
        strict: If True, any coverage gap causes failure.

    Returns:
        {
            "status": "passed" | "failed",
            "gaps": [ { "question_id": "Q1", "gap_type": "modeling", "detail": "..." } ],
        }
    """
    case_dir = Path(case_dir).resolve()

    # Load method plans
    plan_summary = read_official_json(case_dir, "workspace/method_plan/case.method_plan_summary.json", {}) or {}
    if not plan_summary.get("plans"):
        out = _fail("NO_METHOD_PLANS", "Run method-plan-synthesize first.", strict)
        out.update({"case_id": case_dir.name, "timestamp": now_iso(), "gaps": [{"question_id": question_id or "ALL", "gap_type": "method_plan_missing", "detail": "No method plan summary found.", "action": "Run method-recommend and method-plan-synthesize after academic-search."}], "gap_count": 1})
        write_report_json(case_dir, "quality/coverage_gap_analysis.json", out)
        return out

    # Load signatures for requirement comparison
    signatures = read_official_json(case_dir, "workspace/problem_signatures/case.signatures.json", {}) or {}

    gaps = []
    for qid, plan in plan_summary.get("plans", {}).items():
        sig = signatures.get("questions", {}).get(qid, {})
        q_gaps = _check_one(qid, plan, sig)
        gaps.extend(q_gaps)

    out = {
        "status": "passed" if not gaps else "failed",
        "case_id": case_dir.name,
        "timestamp": now_iso(),
        "gaps": gaps,
        "gap_count": len(gaps),
    }
    write_report_json(case_dir, "quality/coverage_gap_analysis.json", out)

    if strict and gaps:
        gap_descriptions = [f"{g['question_id']}:{g['gap_type']}" for g in gaps]
        raise RuntimeError(
            f"Coverage gaps detected: {gap_descriptions}. "
            f"Execute additional academic searches to fill these gaps. "
            f"No self-knowledge gap-filling is permitted."
        )

    return out


def _check_one(qid: str, plan: dict, signature: dict) -> list[dict]:
    """Check coverage for one question."""
    gaps = []

    # 1. Modeling coverage
    tasks = signature.get("task_archetypes", [])
    if tasks and not plan.get("primary_model"):
        gaps.append({
            "question_id": qid,
            "gap_type": "modeling",
            "detail": f"No primary model for tasks: {[t.get('task') for t in tasks]}",
            "action": "Execute academic search for primary modeling approach.",
        })

    # 2. Alternative model coverage
    if len(plan.get("alternative_models", [])) < 2:
        gaps.append({
            "question_id": qid,
            "gap_type": "model_diversity",
            "detail": "Fewer than 2 alternative models — insufficient for tournament comparison.",
            "action": "Search for alternative modeling approaches to the same problem.",
        })

    # 3. Solution coverage
    if tasks and any(t.get("task") in ("constrained_optimization", "optimization") for t in tasks):
        if not plan.get("optimization_method"):
            gaps.append({
                "question_id": qid,
                "gap_type": "solution",
                "detail": "Optimization task but no optimization method in plan.",
                "action": "Search for optimization algorithms applicable to this model.",
            })

    # 4. Verification coverage
    if not plan.get("verification_approach"):
        gaps.append({
            "question_id": qid,
            "gap_type": "verification",
            "detail": "No independent verification approach specified.",
            "action": "Search for independent verification methods for this model type.",
        })

    # 5. Citation coverage
    if plan.get("citation_count", 0) == 0:
        gaps.append({
            "question_id": qid,
            "gap_type": "citations",
            "detail": "Zero literature citations in method plan.",
            "action": "All methods must reference academic search results.",
        })

    # 6. Constraint coverage
    sig_constraints = signature.get("constraints", [])
    if sig_constraints and not plan.get("optimization_method"):
        gaps.append({
            "question_id": qid,
            "gap_type": "constraint_handling",
            "detail": f"Constraints present ({sig_constraints[:3]}) but no optimization method.",
            "action": "Search for constraint handling methods.",
        })

    return gaps


def _fail(code: str, message: str, strict: bool) -> dict:
    result = {"status": "failed", "code": code, "message": message}
    if strict:
        raise RuntimeError(f"[{code}] {message}")
    return result
