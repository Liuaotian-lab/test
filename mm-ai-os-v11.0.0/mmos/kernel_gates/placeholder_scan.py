from __future__ import annotations

from pathlib import Path
import re

from .common import status_from
from mmos.kernel.jsonio import write_json

LINE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("TODO", re.compile(r"\bTODO\b", re.I)),
    ("FIXME", re.compile(r"\bFIXME\b", re.I)),
    ("NOT_IMPLEMENTED", re.compile(r"NotImplemented|raise\s+NotImplementedError", re.I)),
    ("RETURN_TRUE", re.compile(r"^\s*return\s+True\s*(#.*)?$")),
    ("RETURN_EMPTY_LIST", re.compile(r"^\s*return\s+\[\]\s*(#.*)?$")),
    ("RETURN_EMPTY_DICT", re.compile(r"^\s*return\s+\{\}\s*(#.*)?$")),
    ("PASS_STMT", re.compile(r"^\s*pass\s*(#.*)?$")),
    ("TEMPLATE_PLACEHOLDER", re.compile(r"template_placeholder|mock_solver|demo_solver|fake_result|dummy_result", re.I)),
]
TEXT_SUFFIXES = {".py", ".md", ".json", ".jsonl", ".yaml", ".yml", ".txt", ".csv"}
SKIP_PARTS = {"__pycache__", ".git", ".pytest_cache", ".mypy_cache", "node_modules"}


def _scan_roots(case_dir: Path, root: Path | None, include_os: bool) -> list[tuple[Path, str]]:
    roots: list[tuple[Path, str]] = []
    for rel in ["engineering/questions", "engineering/results", "results"]:
        p = case_dir / rel
        if p.exists():
            roots.append((p, "case"))
    if include_os and root:
        for rel in ["mmos", "scripts"]:
            p = Path(root) / rel
            if p.exists():
                roots.append((p, "os"))
    return roots


def _should_scan(path: Path) -> bool:
    if any(part in SKIP_PARTS for part in path.parts):
        return False
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    if path.stat().st_size > 512_000:
        return False
    return True


def scan_placeholders(case_dir: Path, *, root: Path | None = None, include_os: bool = False, write: bool = True) -> dict:
    case_dir = Path(case_dir).resolve()
    root = Path(root).resolve() if root else None
    findings: list[dict] = []
    warnings: list[dict] = []

    for scan_root, scope in _scan_roots(case_dir, root, include_os):
        for path in sorted(scan_root.rglob("*")):
            if not path.is_file() or not _should_scan(path):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception as exc:
                warnings.append({"code": "READ_FAILED", "path": str(path), "message": str(exc)})
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                for code, pat in LINE_PATTERNS:
                    if pat.search(line):
                        severity = "blocking" if scope == "case" else "warning"
                        findings.append({
                            "code": code,
                            "severity": severity,
                            "scope": scope,
                            "path": str(path.relative_to(case_dir) if scope == "case" else path.relative_to(root) if root else path),
                            "line": lineno,
                            "text": line.strip()[:240],
                        })
    failures = [f for f in findings if f.get("severity") == "blocking"]
    report = {
        "gate": "placeholder-scan",
        "status": status_from(failures, warnings),
        "case_dir": str(case_dir),
        "include_os": include_os,
        "finding_count": len(findings),
        "findings": findings,
        "failures": failures,
        "warnings": warnings,
    }
    if write:
        write_json(case_dir / "quality" / "placeholder_scan_report.json", report)
    return report
