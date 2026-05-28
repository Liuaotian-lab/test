from __future__ import annotations
from pathlib import Path
from mmos.kernel.jsonio import write_json
from mmos.kernel.events import now_iso

def benchmark_compare(case_dir: Path, benchmark: str | None = None, strict: bool = True) -> dict:
    case_dir = Path(case_dir).resolve()
    report = {
        "gate": "benchmark-compare",
        "status": "failed",
        "code": "BENCHMARKS_NOT_INCLUDED_IN_PURE_DISTRIBUTION",
        "message": "The pure distribution does not include historical benchmark data. Use semantic-audit, method-plan-check and final-gate instead.",
        "generated_at": now_iso(),
    }
    write_json(case_dir / "quality" / "benchmark_compare.json", report)
    if strict:
        raise RuntimeError(report["message"])
    return report
