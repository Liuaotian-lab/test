from __future__ import annotations

from pathlib import Path
from typing import Any

from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel_gates.common import status_from
from mmos.constraints.coverage import constraint_coverage_check
from mmos.dependencies.graph import dependency_check
from mmos.certificates.checker import certificate_check


def semantic_redteam(case_dir: Path, *, all_questions: bool = False) -> dict[str, Any]:
    case_dir = Path(case_dir)
    issues: list[dict[str, Any]] = []
    cov = constraint_coverage_check(case_dir, all_questions=all_questions)
    if cov.get("status") == "failed":
        for f in cov.get("failures", []):
            issues.append({"issue_id": f"sem_cov_{len(issues)+1:03d}", "severity": "blocking", "issue_type": "constraint_coverage_failure", "message": f.get("code", "constraint coverage failure"), "evidence": ["workspace/constraints/reports/constraint_coverage_report.json"], "required_action": "Complete solver hooks, validators, negative tests and certificates for all active constraints.", "status": "open"})
    dep = dependency_check(case_dir, all_questions=all_questions)
    if dep.get("status") == "failed":
        for f in dep.get("failures", []):
            issues.append({"issue_id": f"sem_dep_{len(issues)+1:03d}", "severity": "blocking", "issue_type": "dependency_failure", "message": f.get("code", "dependency failure"), "evidence": ["workspace/dependencies/reports/dependency_check_report.json"], "required_action": "Repair cross-question dependency declarations or required artifacts.", "status": "open"})
    cert = certificate_check(case_dir, all_questions=all_questions)
    if cert.get("status") == "failed":
        for f in cert.get("failures", []):
            issues.append({"issue_id": f"sem_cert_{len(issues)+1:03d}", "severity": "blocking", "issue_type": "certificate_failure", "question_id": f.get("question_id"), "message": f.get("code", "certificate failure"), "evidence": ["quality/certificate_check_report.json"], "required_action": "Provide a passing optimization/boundary certificate or downgrade the claim.", "status": "open"})
    report = {"status": "failed" if any(i.get("severity") == "blocking" and i.get("status") == "open" for i in issues) else "passed", "issues": issues, "failures": issues, "warnings": []}
    write_json(case_dir / "quality" / "semantic_redteam_report.json", report)
    return report


def missing_constraint_probe(case_dir: Path, *, all_questions: bool = False) -> dict[str, Any]:
    return semantic_redteam(case_dir, all_questions=all_questions)


def overclaim_check(case_dir: Path, *, all_questions: bool = False) -> dict[str, Any]:
    return certificate_check(case_dir, all_questions=all_questions)


def model_risk_register(case_dir: Path, *, all_questions: bool = False) -> dict[str, Any]:
    case_dir = Path(case_dir)
    sem = semantic_redteam(case_dir, all_questions=all_questions)
    risks = []
    for issue in sem.get("issues", []):
        risks.append({
            "risk_id": issue.get("issue_id"),
            "question_id": issue.get("question_id"),
            "risk_type": issue.get("issue_type"),
            "severity": issue.get("severity"),
            "description": issue.get("message"),
            "detected_by": "semantic_redteam",
            "required_action": issue.get("required_action"),
            "status": issue.get("status", "open"),
        })
    report = {"status": "failed" if any(r.get("severity") == "blocking" and r.get("status") == "open" for r in risks) else "passed", "risks": risks, "failures": [r for r in risks if r.get("severity") == "blocking" and r.get("status") == "open"], "warnings": []}
    write_json(case_dir / "quality" / "model_risk_register.json", report)
    return report


def model_risk_check(case_dir: Path) -> dict[str, Any]:
    case_dir = Path(case_dir)
    p = case_dir / "quality" / "model_risk_register.json"
    if not p.exists():
        return model_risk_register(case_dir, all_questions=True)
    report = read_json(p, {}) or {}
    risks = report.get("risks", [])
    failures = [r for r in risks if r.get("severity") == "blocking" and r.get("status") == "open"]
    out = {"status": status_from(failures, []), "risks": risks, "failures": failures, "warnings": []}
    write_json(case_dir / "quality" / "model_risk_check_report.json", out)
    return out
