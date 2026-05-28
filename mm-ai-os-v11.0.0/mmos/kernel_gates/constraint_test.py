from __future__ import annotations

from pathlib import Path
import importlib.util
import json
from typing import Any, Callable

from .common import required_questions, status_from
from mmos.kernel.jsonio import write_json


def _load_validator(path: Path):
    spec = importlib.util.spec_from_file_location(f"mmos_dynamic_validator_{abs(hash(path))}", path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _validator_fn(mod) -> Callable[[Any], Any] | None:
    for name in ["validate", "validate_solution", "validate_output", "run_validation"]:
        fn = getattr(mod, name, None)
        if callable(fn):
            return fn
    return None


def _has_violation(result: Any) -> bool:
    if result is False:
        return True
    if isinstance(result, list):
        return len(result) > 0
    if isinstance(result, dict):
        if result.get("status") == "failed":
            return True
        if result.get("violation_count", 0):
            return True
        if result.get("violations"):
            return True
        if result.get("failures"):
            return True
        if result.get("errors"):
            return True
    return False


def _fixture_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    out: list[Path] = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in {".json", ".jsonl", ".yaml", ".yml", ".txt", ".csv", ".py"}:
            out.append(p)
    return out


def _read_fixture(path: Path) -> Any:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return {"fixture_path": str(path), "content": path.read_text(encoding="utf-8", errors="ignore")}


def constraint_test(case_dir: Path, *, question_id: str | None = None, write: bool = True) -> dict:
    case_dir = Path(case_dir).resolve()
    qids = [question_id] if question_id else required_questions(case_dir)
    failures: list[dict] = []
    warnings: list[dict] = []
    questions: list[dict] = []

    if not qids:
        failures.append({"code": "NO_REQUIRED_QUESTIONS", "message": "No required questions found for constraint-test."})

    for qid in qids:
        qdir = case_dir / "engineering" / "questions" / qid
        qreport = {"question_id": qid, "status": "passed", "positive_tests": 0, "negative_tests": 0, "violations_detected": 0, "blocking_issues": []}
        constraints_py = qdir / "constraints.py"
        validators_py = qdir / "validators.py"
        if not constraints_py.exists():
            qreport["blocking_issues"].append({"code": "MISSING_CONSTRAINTS_PY", "path": str(constraints_py.relative_to(case_dir))})
        if not validators_py.exists():
            qreport["blocking_issues"].append({"code": "MISSING_VALIDATORS_PY", "path": str(validators_py.relative_to(case_dir))})
        else:
            import re
            text = validators_py.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"^\s*return\s+True\s*(#.*)?$", text, re.M) or re.search(r"^\s*pass\s*(#.*)?$", text, re.M):
                qreport["blocking_issues"].append({"code": "EMPTY_OR_TRIVIAL_VALIDATOR", "path": str(validators_py.relative_to(case_dir))})

        pos_files = _fixture_files(qdir / "tests" / "positive")
        neg_files = _fixture_files(qdir / "tests" / "negative")
        qreport["positive_tests"] = len(pos_files)
        qreport["negative_tests"] = len(neg_files)
        if not pos_files:
            qreport["blocking_issues"].append({"code": "MISSING_POSITIVE_TEST", "path": str((qdir / "tests" / "positive").relative_to(case_dir))})
        if not neg_files:
            qreport["blocking_issues"].append({"code": "MISSING_NEGATIVE_TEST", "path": str((qdir / "tests" / "negative").relative_to(case_dir))})

        if validators_py.exists() and neg_files:
            try:
                mod = _load_validator(validators_py)
                fn = _validator_fn(mod) if mod else None
                if fn is None:
                    qreport["blocking_issues"].append({"code": "NO_RUNNABLE_VALIDATOR_FUNCTION", "path": str(validators_py.relative_to(case_dir))})
                else:
                    for fixture in neg_files:
                        try:
                            res = fn(_read_fixture(fixture))
                            if _has_violation(res):
                                qreport["violations_detected"] += 1
                        except Exception:
                            qreport["violations_detected"] += 1
                    if qreport["violations_detected"] == 0:
                        qreport["blocking_issues"].append({"code": "NEGATIVE_TEST_DID_NOT_PRODUCE_VIOLATION"})
            except Exception as exc:
                qreport["blocking_issues"].append({"code": "VALIDATOR_EXECUTION_FAILED", "message": str(exc)})

        if qreport["blocking_issues"]:
            qreport["status"] = "failed"
            failures.append({"code": "QUESTION_CONSTRAINT_TEST_FAILED", "question_id": qid, "issues": qreport["blocking_issues"]})
        questions.append(qreport)

    report = {"gate": "constraint-test", "status": status_from(failures, warnings), "case_dir": str(case_dir), "questions": questions, "failures": failures, "warnings": warnings}
    if write:
        write_json(case_dir / "quality" / "constraint_test_report.json", report)
        for q in questions:
            write_json(case_dir / "engineering" / "results" / q["question_id"] / "reports" / "constraint_test_report.json", q)
    return report
