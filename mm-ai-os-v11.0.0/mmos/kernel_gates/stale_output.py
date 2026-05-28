from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import required_questions, sha256_file, solution_paths, status_from
from mmos.kernel.jsonio import read_json, write_json


def _latest_mtime(paths: list[Path]) -> float | None:
    mtimes = [p.stat().st_mtime for p in paths if p.exists() and p.is_file()]
    return max(mtimes) if mtimes else None


def _source_files_for_question(case_dir: Path, qid: str) -> list[Path]:
    roots = [
        case_dir / "engineering" / "questions" / qid,
        case_dir / "questions" / qid,
        case_dir / "contracts" / "questions" / qid,
    ]
    files: list[Path] = []
    for root in roots:
        if root.exists():
            for suffix in ["*.py", "*.json", "*.yaml", "*.yml"]:
                files.extend(root.rglob(suffix))
    return [p for p in files if p.is_file()]


def _qid_from_solution(path: Path, data: dict[str, Any] | None = None) -> str | None:
    if isinstance(data, dict) and data.get("question_id"):
        return str(data.get("question_id"))
    parts = path.parts
    if "results" in parts:
        idx = max(i for i, part in enumerate(parts) if part == "results")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return None


def stale_output_check(case_dir: Path, *, question_id: str | None = None, write: bool = True) -> dict:
    case_dir = Path(case_dir).resolve()
    failures: list[dict] = []
    warnings: list[dict] = []
    checks: list[dict] = []
    paths = solution_paths(case_dir)
    if question_id:
        paths = [p for p in paths if _qid_from_solution(p) == question_id or p.parts[-3] == question_id]
    if not paths:
        failures.append({"code": "NO_SOLUTION_RESULTS_FOUND"})

    for result_path in paths:
        data = read_json(result_path, {}) or {}
        qid = _qid_from_solution(result_path, data) or "unknown"
        check = {"question_id": qid, "result_path": str(result_path.relative_to(case_dir) if str(result_path).startswith(str(case_dir)) else result_path), "status": "passed", "issues": []}
        if not result_path.exists():
            issue = {"code": "MISSING_RESULT", "path": str(result_path)}
            check["issues"].append(issue)
            failures.append(issue)
            checks.append(check)
            continue
        sources = _source_files_for_question(case_dir, qid)
        latest_source = _latest_mtime(sources)
        if latest_source and result_path.stat().st_mtime < latest_source:
            issue = {"code": "STALE_SOLUTION_RESULT", "question_id": qid, "result_path": str(result_path), "source_count": len(sources)}
            check["issues"].append(issue)
            failures.append(issue)
        if not latest_source:
            warnings.append({"code": "NO_SOURCE_FILES_FOR_FRESHNESS_CHECK", "question_id": qid})

        output_hashes = data.get("output_hashes") or {}
        if isinstance(output_hashes, dict):
            for rel, expected in output_hashes.items():
                artifact = Path(str(rel))
                candidates = [case_dir / artifact, result_path.parent / artifact]
                actual_path = next((c for c in candidates if c.exists()), candidates[0])
                if not actual_path.exists():
                    issue = {"code": "HASHED_ARTIFACT_MISSING", "artifact": str(rel)}
                    check["issues"].append(issue)
                    failures.append(issue)
                    continue
                actual = sha256_file(actual_path)
                if actual != expected:
                    issue = {"code": "OUTPUT_HASH_MISMATCH", "artifact": str(rel), "expected": expected, "actual": actual}
                    check["issues"].append(issue)
                    failures.append(issue)
        if check["issues"]:
            check["status"] = "failed"
        checks.append(check)

    report = {"gate": "stale-output-check", "status": status_from(failures, warnings), "case_dir": str(case_dir), "checks": checks, "failures": failures, "warnings": warnings}
    if write:
        write_json(case_dir / "quality" / "stale_output_check_report.json", report)
    return report
