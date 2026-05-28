from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run_cli(*args: str, timeout: int = 180) -> dict:
    with tempfile.TemporaryDirectory() as td:
        out_path = Path(td) / "stdout.json"
        err_path = Path(td) / "stderr.txt"
        with out_path.open("w", encoding="utf-8") as out, err_path.open("w", encoding="utf-8") as err:
            proc = subprocess.run(
                [sys.executable, "-m", "mmos.cli", *args],
                cwd=ROOT,
                text=True,
                stdout=out,
                stderr=err,
                timeout=timeout,
            )
        stdout = out_path.read_text(encoding="utf-8", errors="replace")
        stderr = err_path.read_text(encoding="utf-8", errors="replace")
    assert proc.returncode == 0, stderr + stdout
    return json.loads(stdout)


def test_synthetic_thermal_pipeline_reaches_package_submit() -> None:
    case_id = "synthetic_thermal_minimal_pytest"
    result = run_cli("synthetic-e2e-run", case_id, "--force")
    assert result["status"] == "passed"
    assert result["step_count"] >= 17
    assert result["steps"][-1] == {"step": "package_submit", "status": "ok"}

    case_dir = ROOT / "cases" / case_id
    assert (case_dir / "workspace" / "problem_understanding" / "official" / "final_problem_signature.json").exists()
    assert (case_dir / "workspace" / "academic_search" / "official" / "search_results.json").exists()
    assert (case_dir / "workspace" / "method_plan" / "official" / "case.method_plan_summary.json").exists()

    final_gate = json.loads((case_dir / "final_outputs" / "final_gate_check.json").read_text(encoding="utf-8"))
    assert final_gate["status"] == "passed"
    assert final_gate["final_allowed"] is True

    manifest = json.loads((case_dir / "package" / "package_manifest.json").read_text(encoding="utf-8"))
    assert manifest["zip_path"] == "package/final_submission.zip"
    assert manifest["files"]
    assert (case_dir / "package" / "final_submission.zip").exists()
