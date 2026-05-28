from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import re

from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel_gates.common import required_questions, status_from

_OPT_KEYWORDS = [
    "minimal", "minimum", "maximum", "maximal", "optimal", "earliest", "latest",
    "smallest", "largest", "terminal", "boundary", "critical",
    "最小", "最大", "最优", "终止", "边界", "临界", "上界", "下界",
]


def _question_ids(case_dir: Path, question_id: str | None = None) -> list[str]:
    if question_id:
        return [question_id]
    qids = required_questions(case_dir)
    if not qids:
        qids = sorted({p.parent.parent.name for p in (case_dir / "results").glob("*/outputs/solution_real.json")}) if (case_dir / "results").exists() else []
    return qids


def _certificate_paths(case_dir: Path, qid: str) -> list[Path]:
    return [
        case_dir / "results" / qid / "reports" / "optimization_certificate.json",
        case_dir / "engineering" / "results" / qid / "reports" / "optimization_certificate.json",
    ]


def _load_solution(case_dir: Path, qid: str) -> dict[str, Any]:
    for p in [case_dir / "results" / qid / "outputs" / "solution_real.json", case_dir / "engineering" / "results" / qid / "outputs" / f"solution_{qid}_real.json"]:
        if p.exists():
            obj = read_json(p, {})
            return obj if isinstance(obj, dict) else {}
    return {}


def _needs_certificate_from_solution(solution: dict[str, Any]) -> bool:
    text = json.dumps(solution, ensure_ascii=False).lower()
    if solution.get("optimal") is True:
        return True
    ql = str(solution.get("quality_level", "")).lower()
    if ql in {"global_optimal", "certified_optimal", "exhaustive_best"}:
        return True
    return any(k.lower() in text for k in _OPT_KEYWORDS)


def _claim_texts(case_dir: Path, qid: str) -> list[str]:
    out: list[str] = []
    for p in [case_dir / "reports" / "final_claims.jsonl", case_dir / "reports" / "evidence_claims.jsonl"]:
        if not p.exists():
            continue
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if str(obj.get("question_id")) == qid:
                    out.append(json.dumps(obj, ensure_ascii=False).lower())
    return out


def _needs_certificate(case_dir: Path, qid: str) -> bool:
    sol = _load_solution(case_dir, qid)
    if sol and _needs_certificate_from_solution(sol):
        return True
    return any(any(k.lower() in txt for k in _OPT_KEYWORDS) for txt in _claim_texts(case_dir, qid))


def build_certificate(case_dir: Path, *, question_id: str | None = None) -> dict[str, Any]:
    case_dir = Path(case_dir)
    reports = []
    for qid in _question_ids(case_dir, question_id):
        out = case_dir / "results" / qid / "reports" / "optimization_certificate.json"
        sol = _load_solution(case_dir, qid)
        metrics = sol.get("metrics", {}) if isinstance(sol, dict) else {}
        candidate_value = None
        target = "unspecified"
        if isinstance(metrics, dict) and metrics:
            for k, v in metrics.items():
                if isinstance(v, (int, float)):
                    target, candidate_value = k, v; break
        cert = {
            "certificate_id": f"{qid}_certificate_scaffold",
            "question_id": qid,
            "certificate_type": "bracketing_certificate",
            "target": target,
            "candidate_value": candidate_value,
            "lower_bound": None,
            "upper_bound": None,
            "tolerance": None,
            "feasibility_check": {"status": "unknown", "validators": []},
            "infeasibility_check": {"status": "unknown", "violated_constraints": []},
            "counterexample_probe": {"type": "missing", "status": "missing"},
            "independent_check_status": "missing",
            "certificate_status": "draft",
        }
        write_json(out, cert)
        reports.append({"question_id": qid, "path": str(out), "status": "draft"})
    return {"status": "passed", "certificates": reports}


def _check_one_certificate(cert: dict[str, Any], *, qid: str) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    if not cert.get("certificate_id"):
        failures.append({"code": "MISSING_CERTIFICATE_ID", "question_id": qid})
    if cert.get("question_id") and str(cert.get("question_id")) != qid:
        failures.append({"code": "CERTIFICATE_QUESTION_MISMATCH", "question_id": qid})
    if cert.get("certificate_status") != "pass":
        failures.append({"code": "CERTIFICATE_NOT_PASS", "question_id": qid, "certificate_status": cert.get("certificate_status")})
    # Bracketing minimum/maximum certificates need both feasible and infeasible sides.
    ctype = cert.get("certificate_type", "")
    if ctype in {"bracketing_certificate", "optimization_certificate", "counterexample_certificate"}:
        f = cert.get("feasibility_check", {}) or {}
        inf = cert.get("infeasibility_check", {}) or {}
        if f.get("status") != "feasible":
            failures.append({"code": "MISSING_FEASIBLE_SIDE", "question_id": qid})
        if inf.get("status") != "infeasible":
            failures.append({"code": "MISSING_INFEASIBLE_SIDE", "question_id": qid})
        cp = cert.get("counterexample_probe", {}) or {}
        if cp.get("status") not in {"failed_as_expected", "pass"}:
            failures.append({"code": "MISSING_COUNTEREXAMPLE_PROBE", "question_id": qid})
    return failures


def certificate_check(case_dir: Path, *, question_id: str | None = None, all_questions: bool = False) -> dict[str, Any]:
    case_dir = Path(case_dir)
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    checked = []
    for qid in _question_ids(case_dir, question_id):
        needs = _needs_certificate(case_dir, qid)
        paths = [p for p in _certificate_paths(case_dir, qid) if p.exists()]
        if needs and not paths:
            failures.append({"code": "MISSING_CERTIFICATE", "question_id": qid, "message": "optimal/minimal/maximal/boundary claim requires certificate"})
            checked.append({"question_id": qid, "required": True, "status": "failed"})
            continue
        if not needs and not paths:
            checked.append({"question_id": qid, "required": False, "status": "skipped"})
            continue
        cert = read_json(paths[0], {}) or {}
        cfails = _check_one_certificate(cert, qid=qid)
        failures.extend(cfails)
        checked.append({"question_id": qid, "required": needs, "path": str(paths[0]), "status": "failed" if cfails else "passed"})
    report = {"status": status_from(failures, warnings), "checked": checked, "failures": failures, "warnings": warnings}
    write_json(case_dir / "quality" / "certificate_check_report.json", report)
    return report
