from __future__ import annotations

from pathlib import Path

from .common import status_from
from .placeholder_scan import scan_placeholders
from .constraint_test import constraint_test
from .stale_output import stale_output_check
from .solver_verify import verify_solver_results
from mmos.kernel.jsonio import write_json


def _collect_gate_failure(gate_name: str, report: dict) -> dict | None:
    if report.get("status") == "failed":
        return {"code": "STRICT_GATE_FAILED", "gate": gate_name, "failures": report.get("failures", [])}
    if report.get("status") == "warning":
        return {"code": "STRICT_GATE_WARNING_BLOCKED", "gate": gate_name, "warnings": report.get("warnings", [])}
    return None


def final_strict_gate_check(case_dir: Path, *, root: Path | None = None, write: bool = True) -> dict:
    case_dir = Path(case_dir).resolve()
    root = Path(root).resolve() if root else None
    failures: list[dict] = []
    warnings: list[dict] = []
    gate_results: list[dict] = []

    gates: list[tuple[str, dict]] = []
    gates.append(("placeholder-scan", scan_placeholders(case_dir, root=root, include_os=False, write=write)))
    gates.append(("constraint-test", constraint_test(case_dir, write=write)))
    gates.append(("stale-output-check", stale_output_check(case_dir, write=write)))
    gates.append(("solver-verify", verify_solver_results(case_dir, strict=True, root=root)))
    if (case_dir / 'reports' / 'evidence_claims.jsonl').exists() or (case_dir / 'reports' / 'final_claims.jsonl').exists():
        from mmos.evidence.claim_check import claim_check
        gates.append(("claim-check", claim_check(case_dir, all_claims=True)))
    if any((case_dir / 'reports').glob('red_team_gate_report.json')) or list((case_dir / 'results').rglob('solution_real.json')) or list((case_dir / 'engineering' / 'results').rglob('solution*_real.json')):
        from mmos.quality_protocol.red_team import red_team_gate
        gates.append(("red-team-gate", red_team_gate(case_dir, all_questions=True)))

    for name, report in gates:
        gate_results.append({"gate": name, "status": report.get("status"), "report": report})
        failure = _collect_gate_failure(name, report)
        if failure:
            failures.append(failure)

    report = {
        "gate": "final-gate-strict",
        "status": status_from(failures, warnings),
        "case_dir": str(case_dir),
        "gate_results": gate_results,
        "failures": failures,
        "warnings": warnings,
        "strict": True,
    }
    if write:
        write_json(case_dir / "final_outputs" / "final_gate_strict.json", report)
        write_json(case_dir / "quality" / "final_gate_strict.json", report)
    return report
