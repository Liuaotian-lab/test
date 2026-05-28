from __future__ import annotations

from pathlib import Path

from mmos.kernel_gates.placeholder_scan import scan_placeholders


def test_placeholder_scan_blocks_case_placeholders(tmp_path: Path):
    p = tmp_path / "engineering" / "questions" / "Q1" / "solver.py"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("def solve():\n    return True\n", encoding="utf-8")
    report = scan_placeholders(tmp_path, root=Path.cwd())
    assert report["status"] == "failed"
    assert any(f["code"] == "RETURN_TRUE" for f in report["failures"])
