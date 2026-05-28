from __future__ import annotations

from pathlib import Path
from typing import Any

from mmos.kernel.jsonio import write_json
from mmos.kernel_gates.common import status_from


def _collect(name: str, report: dict[str, Any]) -> dict[str, Any]:
    return {"gate": name, "status": report.get("status"), "report": report}


def _failures_from(name: str, report: dict[str, Any]) -> list[dict[str, Any]]:
    if report.get("status") != "failed":
        return []
    out = []
    for f in report.get("failures", []) or [{"code": "GATE_FAILED"}]:
        if isinstance(f, dict):
            d = dict(f)
        else:
            d = {"message": str(f)}
        d.setdefault("source", name)
        out.append(d)
    return out


def final_gate_v2(case_dir: Path, *, root: Path | None = None, strict: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    artifact: list[dict[str, Any]] = []
    validity: list[dict[str, Any]] = []
    trust: list[dict[str, Any]] = []

    from mmos.kernel_gates.placeholder_scan import scan_placeholders
    from mmos.kernel_gates.stale_output import stale_output_check
    from mmos.kernel_gates.solver_verify import verify_solver_results
    from mmos.validators.negative_tests import negative_test
    from mmos.validators.runner import validator_test
    from mmos.constraints.coverage import constraint_coverage_check
    from mmos.dependencies.graph import dependency_check
    from mmos.certificates.checker import certificate_check
    from mmos.validator_adequacy.adequacy import validator_adequacy_check
    from mmos.evidence.claim_check import claim_check
    from mmos.semantic_redteam.gate import semantic_redteam, model_risk_check

    artifact.append(_collect("placeholder-scan", scan_placeholders(case_dir, root=root, include_os=False, write=True)))
    artifact.append(_collect("stale-output-check", stale_output_check(case_dir, write=True)))
    validity.append(_collect("solver-verify", verify_solver_results(case_dir, strict=True, root=root)))
    # These strict v2 gates are only hard when their source ledgers/reports exist.
    if (case_dir / "workspace" / "constraints").exists():
        validity.append(_collect("constraint-coverage-check", constraint_coverage_check(case_dir, all_questions=True)))
    if (case_dir / "workspace" / "dependencies").exists():
        validity.append(_collect("dependency-check", dependency_check(case_dir, all_questions=True)))
    if (case_dir / "results").exists() or (case_dir / "engineering" / "questions").exists():
        vt = validator_test(case_dir)
        nt = negative_test(case_dir)
        validity.append(_collect("validator-test", vt))
        validity.append(_collect("negative-test", nt))
        if any((case_dir / "results").glob("*/reports/validator_report.json")) or any((case_dir / "engineering" / "results").glob("*/reports/validator_report.json")):
            validity.append(_collect("validator-adequacy-check", validator_adequacy_check(case_dir, all_questions=True)))
    if (case_dir / "reports" / "final_claims.jsonl").exists() or any((case_dir / "results").glob("*/reports/optimization_certificate.json")):
        trust.append(_collect("certificate-check", certificate_check(case_dir, all_questions=True)))
    if (case_dir / "reports" / "final_claims.jsonl").exists() or (case_dir / "reports" / "evidence_claims.jsonl").exists():
        trust.append(_collect("claim-check", claim_check(case_dir, all_claims=True)))
    if (case_dir / "workspace" / "constraints").exists() or (case_dir / "workspace" / "dependencies").exists():
        trust.append(_collect("semantic-redteam", semantic_redteam(case_dir, all_questions=True)))
        trust.append(_collect("model-risk-check", model_risk_check(case_dir)))

    failures: list[dict[str, Any]] = []
    for group in [artifact, validity, trust]:
        for item in group:
            failures.extend(_failures_from(item["gate"], item["report"]))
    report = {
        "gate": "final-gate-v2",
        "status": status_from(failures, []),
        "case_dir": str(case_dir),
        "strict": strict,
        "artifact_gate": "failed" if any(x.get("status") == "failed" for x in artifact) else "passed",
        "validity_gate": "failed" if any(x.get("status") == "failed" for x in validity) else "passed",
        "trust_gate": "failed" if any(x.get("status") == "failed" for x in trust) else "passed",
        "gate_results": {"artifact": artifact, "validity": validity, "trust": trust},
        "blocking_issues": failures,
        "failures": failures,
        "warnings": [],
    }
    write_json(case_dir / "quality" / "final_gate_v2_report.json", report)
    write_json(case_dir / "final_outputs" / "final_gate_v2_report.json", report)
    return report
