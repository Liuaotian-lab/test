from __future__ import annotations

from pathlib import Path
from typing import Any

from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel_gates.common import required_questions, status_from

_CONSTRAINT_TYPES = {
    "objective", "input_data", "output_format", "physical_constraint",
    "geometric_constraint", "statistical_constraint", "optimization_constraint",
    "simulation_invariant", "boundary_condition", "inherited_constraint",
    "inherited_domain_constraint", "claim_limit", "unit_constraint",
    "freshness_constraint",
}


def _ledger_paths(case_dir: Path) -> list[Path]:
    return [
        case_dir / "workspace" / "constraints" / "official" / "constraint_ledger.json",
        case_dir / "workspace" / "constraints" / "candidate" / "constraint_ledger.json",
    ]


def find_constraint_ledger(case_dir: Path) -> Path | None:
    case_dir = Path(case_dir)
    for p in _ledger_paths(case_dir):
        if p.exists():
            return p
    return None


def load_constraint_ledger(case_dir: Path) -> dict[str, Any] | None:
    p = find_constraint_ledger(case_dir)
    if not p:
        return None
    obj = read_json(p, {})
    if isinstance(obj, dict):
        obj.setdefault("case_id", case_dir.name)
        obj.setdefault("constraints", [])
        return obj
    return {"case_id": case_dir.name, "constraints": []}


def build_constraint_ledger(case_dir: Path, *, force: bool = False) -> dict[str, Any]:
    """Build a conservative candidate constraint ledger.

    This command intentionally creates a minimal scaffold rather than guessing
    domain-specific constraints. Strict coverage stays low until solver hooks,
    validators and negative tests are supplied.
    """
    case_dir = Path(case_dir)
    out = case_dir / "workspace" / "constraints" / "candidate" / "constraint_ledger.json"
    if out.exists() and not force:
        return {"status": "passed", "action": "kept_existing", "path": str(out), "ledger": read_json(out, {})}

    constraints: list[dict[str, Any]] = []
    for qid in required_questions(case_dir) or ["Q1"]:
        constraints.append({
            "constraint_id": f"{qid}_OBJ_001",
            "question_id": qid,
            "source_type": "problem_statement",
            "evidence_ids": [],
            "constraint_type": "objective",
            "description": f"Solve required question {qid} according to the problem statement.",
            "depends_on": [],
            "required_solver_hooks": [],
            "required_validators": [],
            "required_negative_tests": [],
            "required_certificates": [],
            "claim_impact": ["feasibility"],
            "status": "active",
        })
        constraints.append({
            "constraint_id": f"{qid}_OUT_001",
            "question_id": qid,
            "source_type": "problem_statement",
            "evidence_ids": [],
            "constraint_type": "output_format",
            "description": f"Required outputs for {qid} must be generated and validated.",
            "depends_on": [],
            "required_solver_hooks": ["output_builder"],
            "required_validators": ["output_template_check"],
            "required_negative_tests": ["missing_required_output"],
            "required_certificates": [],
            "claim_impact": ["output"],
            "status": "active",
        })
    ledger = {"case_id": case_dir.name, "schema_version": "10.0", "constraints": constraints}
    write_json(out, ledger)
    return {"status": "passed", "action": "created", "path": str(out), "constraint_count": len(constraints)}


def promote_constraint_ledger(case_dir: Path) -> dict[str, Any]:
    case_dir = Path(case_dir)
    src = case_dir / "workspace" / "constraints" / "candidate" / "constraint_ledger.json"
    dst = case_dir / "workspace" / "constraints" / "official" / "constraint_ledger.json"
    if not src.exists():
        return {"status": "failed", "failures": [{"code": "MISSING_CANDIDATE_LEDGER", "path": str(src)}]}
    report = check_constraint_ledger(case_dir, prefer_candidate=True)
    if report.get("status") == "failed":
        return report
    write_json(dst, read_json(src, {}))
    return {"status": "passed", "source": str(src), "destination": str(dst)}


def check_constraint_ledger(case_dir: Path, *, prefer_candidate: bool = False) -> dict[str, Any]:
    case_dir = Path(case_dir)
    path = None
    candidates = list(reversed(_ledger_paths(case_dir))) if prefer_candidate else _ledger_paths(case_dir)
    for p in candidates:
        if p.exists():
            path = p; break
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if not path:
        failures.append({"code": "MISSING_CONSTRAINT_LEDGER", "message": "constraint_ledger.json not found"})
        report = {"status": "failed", "failures": failures, "warnings": warnings}
        write_json(case_dir / "workspace" / "constraints" / "reports" / "constraint_ledger_check.json", report)
        return report
    obj = read_json(path, {})
    constraints = obj.get("constraints", []) if isinstance(obj, dict) else []
    if not isinstance(constraints, list) or not constraints:
        failures.append({"code": "EMPTY_CONSTRAINT_LEDGER", "path": str(path)})
    ids: set[str] = set()
    for idx, c in enumerate(constraints):
        loc = {"index": idx, "constraint_id": c.get("constraint_id") if isinstance(c, dict) else None}
        if not isinstance(c, dict):
            failures.append({"code": "INVALID_CONSTRAINT_ITEM", **loc}); continue
        cid = str(c.get("constraint_id") or "")
        if not cid:
            failures.append({"code": "MISSING_CONSTRAINT_ID", **loc})
        elif cid in ids:
            failures.append({"code": "DUPLICATE_CONSTRAINT_ID", "constraint_id": cid})
        ids.add(cid)
        if not c.get("question_id"):
            failures.append({"code": "MISSING_QUESTION_ID", **loc})
        ctype = c.get("constraint_type")
        if ctype not in _CONSTRAINT_TYPES:
            failures.append({"code": "UNKNOWN_CONSTRAINT_TYPE", "constraint_type": ctype, **loc})
        if not c.get("description"):
            failures.append({"code": "MISSING_DESCRIPTION", **loc})
        if "inherited" in str(ctype) and not c.get("depends_on"):
            failures.append({"code": "INHERITED_CONSTRAINT_WITHOUT_DEPENDS_ON", **loc})
    report = {"status": status_from(failures, warnings), "path": str(path), "constraint_count": len(constraints), "failures": failures, "warnings": warnings}
    write_json(case_dir / "workspace" / "constraints" / "reports" / "constraint_ledger_check.json", report)
    return report
