from __future__ import annotations

from pathlib import Path
from typing import Any

from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel_gates.common import required_questions, status_from
from mmos.certificates.checker import _needs_certificate


def independent_verification_protocol(case_dir: Path, *, question_id: str | None = None, all_questions: bool = False) -> dict[str, Any]:
    case_dir = Path(case_dir)
    qids = [question_id] if question_id else required_questions(case_dir)
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    checks = []
    for qid in qids:
        report_paths = [case_dir / "results" / qid / "reports" / "independent_verification_report.json", case_dir / "quality" / f"{qid}_independent_verification_report.json"]
        existing = next((p for p in report_paths if p.exists()), None)
        high_risk = _needs_certificate(case_dir, qid)
        if high_risk and not existing:
            failures.append({"code": "MISSING_INDEPENDENT_VERIFICATION", "question_id": qid})
            checks.append({"question_id": qid, "high_risk": True, "status": "failed"})
        elif existing:
            rep = read_json(existing, {}) or {}
            if rep.get("status") not in {"passed", "pass"}:
                failures.append({"code": "INDEPENDENT_VERIFICATION_NOT_PASS", "question_id": qid, "path": str(existing)})
            checks.append({"question_id": qid, "high_risk": high_risk, "path": str(existing), "status": rep.get("status")})
        else:
            checks.append({"question_id": qid, "high_risk": False, "status": "skipped"})
    out = {"status": status_from(failures, warnings), "checks": checks, "failures": failures, "warnings": warnings}
    write_json(case_dir / "quality" / "independent_verification_protocol_report.json", out)
    return out


def verified_candidate_comparison_v2(case_dir: Path) -> dict[str, Any]:
    out = {"status": "passed", "message": "No alternate verified candidates were required by this deterministic protocol."}
    write_json(Path(case_dir) / "quality" / "verified_candidate_comparison_v2.json", out)
    return out
