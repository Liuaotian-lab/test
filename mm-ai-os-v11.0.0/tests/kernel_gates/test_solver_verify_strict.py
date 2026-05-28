from __future__ import annotations

from pathlib import Path

from mmos.kernel.jsonio import write_json
from mmos.kernel_gates.solver_verify import verify_solver_result, verify_solver_results


def _valid_solution(case: Path, qid: str = "Q1") -> Path:
    out = case / "results" / qid / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    artifact = out / "result.xlsx"
    artifact.write_text("not a real xlsx; fixture only", encoding="utf-8")
    sol = out / "solution_real.json"
    write_json(sol, {
        "question_id": qid,
        "scope": "real",
        "data_source": "problem_statement_derived",
        "experiment_id": f"{qid}_exp_001",
        "model": "fixture_model",
        "method": "deterministic_fixture",
        "quality_level": "local_optimal",
        "solver_status": "completed",
        "optimal": False,
        "metrics": {"objective_value": 1.0},
        "violation_count": 0,
        "diagnostics": {
            "constraints_checked": True,
            "domain_validators_run": ["fixture_validator"],
            "fallback_used": False,
        },
        "artifacts": [f"results/{qid}/outputs/result.xlsx"],
        "limitations": "Fixture result for strict solver gate tests.",
    })
    return sol


def test_strict_solver_verify_accepts_real_solution(tmp_path: Path):
    sol = _valid_solution(tmp_path)
    report = verify_solver_result(sol, case_dir=tmp_path, strict=True, root=Path.cwd())
    assert report["status"] == "passed"


def test_wrong_demo_data_solution_must_fail(tmp_path: Path):
    sol = _valid_solution(tmp_path)
    data = __import__("json").loads(sol.read_text(encoding="utf-8"))
    data["data_source"] = "demo_data"
    write_json(sol, data)
    report = verify_solver_result(sol, case_dir=tmp_path, strict=True, root=Path.cwd())
    assert report["status"] == "failed"
    assert any(f["code"] == "DEMO_DATA_BLOCKED" for f in report["failures"])


def test_wrong_optimal_claim_must_fail(tmp_path: Path):
    sol = _valid_solution(tmp_path)
    data = __import__("json").loads(sol.read_text(encoding="utf-8"))
    data["quality_level"] = "heuristic_feasible"
    data["optimal"] = True
    write_json(sol, data)
    report = verify_solver_result(sol, case_dir=tmp_path, strict=True, root=Path.cwd())
    assert report["status"] == "failed"
    assert any(f["code"] == "NON_CERTIFIED_QUALITY_CANNOT_BE_OPTIMAL" for f in report["failures"])


def test_wrong_violation_count_must_fail(tmp_path: Path):
    sol = _valid_solution(tmp_path)
    data = __import__("json").loads(sol.read_text(encoding="utf-8"))
    data["violation_count"] = 1
    write_json(sol, data)
    report = verify_solver_result(sol, case_dir=tmp_path, strict=True, root=Path.cwd())
    assert any(f["code"] == "VIOLATION_COUNT_NOT_ZERO" for f in report["failures"])


def test_wrong_missing_artifact_must_fail(tmp_path: Path):
    sol = _valid_solution(tmp_path)
    data = __import__("json").loads(sol.read_text(encoding="utf-8"))
    data["artifacts"] = ["results/Q1/outputs/missing.xlsx"]
    write_json(sol, data)
    report = verify_solver_result(sol, case_dir=tmp_path, strict=True, root=Path.cwd())
    assert any(f["code"] == "ARTIFACT_NOT_FOUND" for f in report["failures"])


def test_strict_solver_verify_all_finds_required_question(tmp_path: Path):
    write_json(tmp_path / "registry" / "questions_registry.json", {"questions": [{"question_id": "Q1", "required": True}]})
    _valid_solution(tmp_path)
    report = verify_solver_results(tmp_path, strict=True, root=Path.cwd())
    assert report["status"] == "passed"
    assert report["result_count"] == 1
