from __future__ import annotations

import json
from pathlib import Path

from mmos.synthetic.thermal_case import run_synthetic_e2e, write_golden_snapshot

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = ROOT / "tests" / "fixtures" / "synthetic_cases" / "thermal_optimization_minimal" / "expected"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_synthetic_pipeline_golden_snapshots_are_stable(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(ROOT)
    case_dir = ROOT / "cases" / "synthetic_thermal_minimal"
    result = run_synthetic_e2e(case_dir, force=True)
    assert result["status"] == "passed"

    snapshot_dir = tmp_path / "golden"
    write_golden_snapshot(case_dir, snapshot_dir)

    for name in [
        "problem_graph.golden.json",
        "search_plan.golden.json",
        "method_plan.golden.json",
        "package_manifest.golden.json",
    ]:
        assert load_json(snapshot_dir / name) == load_json(EXPECTED / name), name
