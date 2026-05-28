"""Compatibility wrapper for v7.1 Problem Understanding Engine.

`problem-signature-extract` is retained for workflow compatibility, but the canonical
artifact is now `workspace/problem_understanding/final_problem_signature.json`.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import read_json
from mmos.problem_understanding.orchestrator import understand_problem, build_compat_signature

SCHEMA_VERSION = "7.4.0"


def extract_problem_signature(case_dir: Path, question_id: str | None = None) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    understand_problem(case_dir, question_id=question_id, strict=False)
    compat_path = case_dir / "workspace" / "problem_signatures" / "case.signatures.json"
    compat = read_json(compat_path, None)
    if compat:
        return compat
    final_sig = read_json(case_dir / "workspace" / "problem_understanding" / "final_problem_signature.json", {}) or {}
    return build_compat_signature(final_sig, case_dir.name)
