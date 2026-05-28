from __future__ import annotations

from pathlib import Path
from typing import Iterable
import hashlib

from mmos.kernel.jsonio import read_json, write_json


def status_from(failures: list[dict], warnings: list[dict]) -> str:
    if failures:
        return "failed"
    if warnings:
        return "warning"
    return "passed"


def infer_case_dir_from_result(path: Path) -> Path | None:
    path = Path(path).resolve()
    parts = path.parts
    # .../<case>/results/<QID>/outputs/solution_real.json
    if "results" in parts:
        idxs = [i for i, p in enumerate(parts) if p == "results"]
        for idx in reversed(idxs):
            if idx > 0:
                return Path(*parts[:idx])
    # .../<case>/engineering/results/<QID>/outputs/solution_QID_real.json
    if "engineering" in parts:
        idxs = [i for i, p in enumerate(parts) if p == "engineering"]
        for idx in reversed(idxs):
            if idx > 0:
                return Path(*parts[:idx])
    return None


def required_questions(case_dir: Path) -> list[str]:
    case_dir = Path(case_dir)
    reg = read_json(case_dir / "registry" / "questions_registry.json", {"questions": []}) or {"questions": []}
    qids: list[str] = []
    for q in reg.get("questions", []) if isinstance(reg, dict) else []:
        if q.get("required", True) is False:
            continue
        qid = q.get("question_id") or q.get("id")
        if qid:
            qids.append(str(qid))
    if qids:
        return sorted(dict.fromkeys(qids))
    # fallback to existing engineering/results or results directories
    for root in [case_dir / "results", case_dir / "engineering" / "results", case_dir / "engineering" / "questions"]:
        if root.exists():
            for child in root.iterdir():
                if child.is_dir():
                    qids.append(child.name)
    return sorted(dict.fromkeys(qids))


def solution_paths(case_dir: Path, *, all_questions: bool = True, explicit: str | None = None) -> list[Path]:
    case_dir = Path(case_dir)
    if explicit:
        p = Path(explicit)
        candidates = [p] if p.is_absolute() else [case_dir / p, case_dir.parent / p, p]
        return [next((c.resolve() for c in candidates if c.exists()), candidates[0].resolve())]
    paths: list[Path] = []
    qids = required_questions(case_dir)
    if qids:
        for qid in qids:
            candidates = [
                case_dir / "results" / qid / "outputs" / "solution_real.json",
                case_dir / "engineering" / "results" / qid / "outputs" / f"solution_{qid}_real.json",
                case_dir / "engineering" / "results" / qid / "outputs" / "solution_real.json",
            ]
            existing = [p for p in candidates if p.exists()]
            paths.extend(existing if existing else [candidates[0]])
    if not paths:
        paths.extend((case_dir / "results").glob("*/outputs/solution_real.json") if (case_dir / "results").exists() else [])
        paths.extend((case_dir / "engineering" / "results").glob("*/outputs/*real*.json") if (case_dir / "engineering" / "results").exists() else [])
    seen: set[str] = set()
    unique: list[Path] = []
    for p in paths:
        key = str(p.resolve())
        if key not in seen:
            seen.add(key)
            unique.append(p.resolve())
    return unique


def resolve_artifact_path(case_dir: Path | None, result_path: Path, artifact: str) -> Path:
    p = Path(artifact)
    if p.is_absolute():
        return p
    candidates: list[Path] = []
    if case_dir:
        candidates.append(case_dir / p)
    candidates.append(result_path.parent / p)
    candidates.append(Path.cwd() / p)
    for c in candidates:
        if c.exists():
            return c.resolve()
    return candidates[0].resolve() if candidates else p.resolve()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_gate_report(path: Path, report: dict) -> dict:
    write_json(Path(path), report)
    return report
