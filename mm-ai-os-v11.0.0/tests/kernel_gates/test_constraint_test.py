from __future__ import annotations

from pathlib import Path

from mmos.kernel.jsonio import write_json
from mmos.kernel_gates.constraint_test import constraint_test


def _scaffold(case: Path):
    qdir = case / "engineering" / "questions" / "Q1"
    (qdir / "tests" / "positive").mkdir(parents=True, exist_ok=True)
    (qdir / "tests" / "negative").mkdir(parents=True, exist_ok=True)
    (qdir / "constraints.py").write_text("MAX_VALUE = 10\n", encoding="utf-8")
    (qdir / "validators.py").write_text(
        "def validate(data):\n"
        "    failures = []\n"
        "    if data.get('value', 0) > 10:\n"
        "        failures.append({'code': 'TOO_LARGE'})\n"
        "    return {'status': 'failed' if failures else 'passed', 'failures': failures, 'violation_count': len(failures)}\n",
        encoding="utf-8",
    )
    write_json(qdir / "tests" / "positive" / "ok.json", {"value": 1})
    write_json(qdir / "tests" / "negative" / "bad.json", {"value": 99})


def test_constraint_test_requires_positive_and_negative_tests(tmp_path: Path):
    write_json(tmp_path / "registry" / "questions_registry.json", {"questions": [{"question_id": "Q1", "required": True}]})
    _scaffold(tmp_path)
    report = constraint_test(tmp_path)
    assert report["status"] == "passed"
    assert report["questions"][0]["violations_detected"] == 1


def test_wrong_empty_validator_must_fail(tmp_path: Path):
    write_json(tmp_path / "registry" / "questions_registry.json", {"questions": [{"question_id": "Q1", "required": True}]})
    qdir = tmp_path / "engineering" / "questions" / "Q1"
    (qdir / "tests" / "positive").mkdir(parents=True, exist_ok=True)
    (qdir / "tests" / "negative").mkdir(parents=True, exist_ok=True)
    (qdir / "constraints.py").write_text("MAX_VALUE = 10\n", encoding="utf-8")
    (qdir / "validators.py").write_text("def validate(data):\n    return True\n", encoding="utf-8")
    write_json(qdir / "tests" / "positive" / "ok.json", {"value": 1})
    write_json(qdir / "tests" / "negative" / "bad.json", {"value": 99})
    report = constraint_test(tmp_path)
    assert report["status"] == "failed"
    assert any(issue["code"] == "EMPTY_OR_TRIVIAL_VALIDATOR" for issue in report["questions"][0]["blocking_issues"])
