from __future__ import annotations

from pathlib import Path
from typing import Any

from mmos.kernel.jsonio import write_json
from mmos.kernel_gates.common import status_from
from .ledger import load_constraint_ledger, check_constraint_ledger

_DOMAIN_TYPES = {
    "physical_constraint", "geometric_constraint", "statistical_constraint",
    "optimization_constraint", "simulation_invariant", "boundary_condition",
    "inherited_constraint", "inherited_domain_constraint", "unit_constraint",
}


def _has_nonempty_list(obj: dict[str, Any], key: str) -> bool:
    value = obj.get(key, [])
    return isinstance(value, list) and len([x for x in value if str(x).strip()]) > 0


def constraint_coverage_check(case_dir: Path, *, all_questions: bool = False) -> dict[str, Any]:
    case_dir = Path(case_dir)
    ledger_check = check_constraint_ledger(case_dir)
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if ledger_check.get("status") == "failed":
        failures.extend(ledger_check.get("failures", []))
        report = {"status": "failed", "coverage_ratio": 0.0, "covered_constraints": 0, "total_constraints": 0, "failures": failures, "warnings": warnings}
        write_json(case_dir / "workspace" / "constraints" / "reports" / "constraint_coverage_report.json", report)
        return report
    ledger = load_constraint_ledger(case_dir) or {"constraints": []}
    constraints = [c for c in ledger.get("constraints", []) if isinstance(c, dict) and c.get("status", "active") == "active"]
    covered = 0
    items: list[dict[str, Any]] = []
    for c in constraints:
        cid = c.get("constraint_id")
        ctype = c.get("constraint_type")
        item_failures: list[dict[str, Any]] = []
        if not _has_nonempty_list(c, "required_solver_hooks"):
            item_failures.append({"code": "MISSING_SOLVER_HOOK", "constraint_id": cid})
        needs_validator = ctype == "output_format" or ctype in _DOMAIN_TYPES
        if needs_validator and not _has_nonempty_list(c, "required_validators"):
            item_failures.append({"code": "MISSING_VALIDATOR", "constraint_id": cid})
        if needs_validator and not _has_nonempty_list(c, "required_negative_tests"):
            item_failures.append({"code": "MISSING_NEGATIVE_TEST", "constraint_id": cid})
        impacts = {str(x).lower() for x in c.get("claim_impact", []) if isinstance(c.get("claim_impact", []), list)}
        needs_certificate = bool(c.get("required_certificates")) or ctype == "optimization_constraint" or any(x in impacts for x in ["minimality", "maximality", "optimality", "boundary", "terminal"])
        if needs_certificate and not _has_nonempty_list(c, "required_certificates"):
            item_failures.append({"code": "MISSING_REQUIRED_CERTIFICATE", "constraint_id": cid})
        if "inherited" in str(ctype) and not _has_nonempty_list(c, "depends_on"):
            item_failures.append({"code": "MISSING_DEPENDS_ON", "constraint_id": cid})
        if not item_failures:
            covered += 1
        else:
            failures.extend(item_failures)
        items.append({"constraint_id": cid, "question_id": c.get("question_id"), "covered": not item_failures, "failures": item_failures})
    ratio = float(covered / len(constraints)) if constraints else 0.0
    report = {
        "status": status_from(failures, warnings),
        "coverage_ratio": ratio,
        "covered_constraints": covered,
        "total_constraints": len(constraints),
        "items": items,
        "failures": failures,
        "warnings": warnings,
    }
    write_json(case_dir / "workspace" / "constraints" / "reports" / "constraint_coverage_report.json", report)
    return report
