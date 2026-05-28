from __future__ import annotations

from pathlib import Path
from typing import Any

from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel_gates.common import required_questions, status_from


def _question_ids(case_dir: Path, question_id: str | None = None) -> list[str]:
    return [question_id] if question_id else required_questions(case_dir)


def _reports_for(case_dir: Path, qid: str) -> list[Path]:
    return [
        case_dir / "results" / qid / "reports" / "validator_report.json",
        case_dir / "engineering" / "results" / qid / "reports" / "validator_report.json",
        case_dir / "engineering" / "questions" / qid / "validator_report.json",
    ]


def validator_adequacy_check(case_dir: Path, *, question_id: str | None = None, all_questions: bool = False) -> dict[str, Any]:
    case_dir = Path(case_dir)
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    for qid in _question_ids(case_dir, question_id):
        reports = [p for p in _reports_for(case_dir, qid) if p.exists()]
        if not reports:
            failures.append({"code": "MISSING_VALIDATOR_REPORT", "question_id": qid})
            items.append({"question_id": qid, "status": "failed"})
            continue
        rep = read_json(reports[0], {}) or {}
        validators = rep.get("validators", []) if isinstance(rep, dict) else []
        if not validators:
            failures.append({"code": "EMPTY_VALIDATOR_REPORT", "question_id": qid})
        for v in validators:
            vid = v.get("validator_id") if isinstance(v, dict) else None
            pf = int(v.get("positive_tests", 0) or 0) if isinstance(v, dict) else 0
            nf = int(v.get("negative_tests", 0) or 0) if isinstance(v, dict) else 0
            vd = int(v.get("violations_detected", 0) or 0) if isinstance(v, dict) else 0
            mut = v.get("mutation_detected", v.get("adversarial_detected", None)) if isinstance(v, dict) else None
            if pf <= 0:
                failures.append({"code": "VALIDATOR_NO_POSITIVE_TEST", "question_id": qid, "validator_id": vid})
            if nf <= 0 or vd <= 0:
                failures.append({"code": "VALIDATOR_NO_NEGATIVE_DETECTION", "question_id": qid, "validator_id": vid})
            if mut is False:
                failures.append({"code": "VALIDATOR_FAILED_MUTATION", "question_id": qid, "validator_id": vid})
            elif mut is None:
                warnings.append({"code": "VALIDATOR_NO_MUTATION_REPORT", "question_id": qid, "validator_id": vid})
        items.append({"question_id": qid, "path": str(reports[0]), "validator_count": len(validators), "status": "passed"})
    report = {"status": status_from(failures, warnings), "items": items, "failures": failures, "warnings": warnings}
    write_json(case_dir / "quality" / "validator_adequacy_report.json", report)
    return report


def adversarial_test_build(case_dir: Path, *, question_id: str | None = None) -> dict[str, Any]:
    case_dir = Path(case_dir)
    qids = _question_ids(case_dir, question_id) or ["Q1"]
    built = []
    for qid in qids:
        p = case_dir / "engineering" / "questions" / qid / "tests" / "negative" / "adversarial_mutation.json"
        write_json(p, {"case": "adversarial_mutation", "question_id": qid, "expected_violation": True})
        built.append(str(p))
    return {"status": "passed", "built": built}


def adversarial_test_run(case_dir: Path, *, question_id: str | None = None) -> dict[str, Any]:
    # The deterministic runtime delegates actual detection to validator_adequacy_check.
    return validator_adequacy_check(case_dir, question_id=question_id)
