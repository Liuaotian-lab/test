from __future__ import annotations

from pathlib import Path
import os
import time

from mmos.kernel.jsonio import write_json
from mmos.kernel_gates.stale_output import stale_output_check


def test_wrong_stale_output_must_fail(tmp_path: Path):
    write_json(tmp_path / "registry" / "questions_registry.json", {"questions": [{"question_id": "Q1", "required": True}]})
    out = tmp_path / "results" / "Q1" / "outputs"
    out.mkdir(parents=True)
    sol = out / "solution_real.json"
    write_json(sol, {"question_id": "Q1"})
    old = time.time() - 100
    os.utime(sol, (old, old))
    src = tmp_path / "engineering" / "questions" / "Q1" / "run.py"
    src.parent.mkdir(parents=True)
    src.write_text("print('new source')\n", encoding="utf-8")
    now = time.time()
    os.utime(src, (now, now))
    report = stale_output_check(tmp_path)
    assert report["status"] == "failed"
    assert any(f["code"] == "STALE_SOLUTION_RESULT" for f in report["failures"])
