from __future__ import annotations

from pathlib import Path

from mmos.kernel_gates.solver_verify import verify_solver_result as _verify_solver_result


def verify_solver_result(path: Path, strict_schema: bool = False, **kwargs) -> dict:
    """Backward-compatible wrapper for the 8.0.1 strict kernel verifier.

    Existing callers keep the permissive legacy behavior unless strict_schema or
    strict=True is requested.  New final-gate --strict routes through
    mmos.kernel_gates directly.
    """
    strict = bool(kwargs.pop("strict", False) or strict_schema)
    return _verify_solver_result(Path(path), strict=strict, strict_schema=strict_schema, **kwargs)
