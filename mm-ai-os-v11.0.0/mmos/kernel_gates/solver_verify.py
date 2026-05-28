from __future__ import annotations

from pathlib import Path
from typing import Any
import re

from mmos.core.schema import validate_data
from mmos.kernel.jsonio import read_json
from mmos.kernel.quality import validate_quality_claim
from .common import infer_case_dir_from_result, resolve_artifact_path, solution_paths, status_from

LEGACY_REQUIRED_FIELDS = ["question_id", "status", "quality_level", "diagnostics"]
BLOCKED_SOLVER_PAT = re.compile(r"placeholder|template_placeholder|dummy|mock|toy|demo_solver|fake_result|constant_result", re.I)
TERMINAL_BAD_STATUSES = {"failed", "timeout", "iter_limit"}
NON_CERTIFIED_OPTIMAL_TRUE = {"heuristic_feasible", "simulation_estimate", "approximate", "exploratory"}


def _string_blob(result: dict) -> str:
    parts: list[str] = []
    for key in ["solver_name", "method", "model", "model_name", "algorithm"]:
        if result.get(key) is not None:
            parts.append(str(result.get(key)))
    diag = result.get("diagnostics", {}) or {}
    if isinstance(diag, dict):
        for key in ["solver_name", "method", "model", "model_name", "algorithm"]:
            if diag.get(key) is not None:
                parts.append(str(diag.get(key)))
        parts.extend(str(x) for x in diag.get("warnings", []) if x is not None)
    return " ".join(parts)


def _has_numeric_metric(result: dict) -> bool:
    for key in ["objective_value", "score", "value", "annual_output_mw", "unit_area_output_kw_m2"]:
        if isinstance(result.get(key), (int, float)) and not isinstance(result.get(key), bool):
            return True
    metrics = result.get("metrics") or {}
    if isinstance(metrics, dict):
        return any(isinstance(v, (int, float)) and not isinstance(v, bool) for v in metrics.values())
    return False


def _schema_failures(result: Any, root: Path | None = None) -> tuple[list[dict], dict]:
    validation = validate_data(result, "solver/solution_real", root=root)
    failures: list[dict] = []
    for err in validation.errors:
        failures.append({"code": "SOLUTION_REAL_SCHEMA_ERROR", **err})
    return failures, validation.to_dict()


def verify_solver_result(path: Path, *, case_dir: Path | None = None, strict: bool = False, strict_schema: bool = False, root: Path | None = None) -> dict:
    result_path = Path(path).resolve()
    result = read_json(result_path, default=None)
    failures: list[dict] = []
    warnings: list[dict] = []
    schema_report: dict | None = None
    case_dir = Path(case_dir).resolve() if case_dir else infer_case_dir_from_result(result_path)

    if result is None or not isinstance(result, dict):
        failures.append({"code": "RESULT_NOT_FOUND", "message": f"missing or invalid JSON: {result_path}"})
        return {"gate": "solver-verify", "status": "failed", "failures": failures, "warnings": warnings, "result_path": str(result_path), "strict": bool(strict or strict_schema)}

    blob = _string_blob(result)
    if BLOCKED_SOLVER_PAT.search(blob):
        failures.append({"code": "PLACEHOLDER_SOLVER_BLOCKED", "message": "placeholder/template/dummy/mock/toy/demo solvers are not allowed in real competition runs", "evidence": blob[:300]})

    # Backward-compatible legacy verification stays permissive unless strict is requested.
    if not strict and not strict_schema:
        for key in LEGACY_REQUIRED_FIELDS:
            if key not in result:
                failures.append({"code": "MISSING_FIELD", "field": key, "message": f"missing required field {key}"})
        failures.extend(validate_quality_claim(result))
        diag = result.get("diagnostics", {}) or {}
        if result.get("status") in {"success", "ok", "passed"} and not _has_numeric_metric(result):
            failures.append({"code": "NO_NUMERIC_RESULT_METRIC", "message": "A successful solver result must expose at least one numeric objective or metric."})
        if result.get("stage") == "real" and result.get("quality_level") in {"exploratory", "failed", None}:
            failures.append({"code": "REAL_RESULT_QUALITY_TOO_LOW", "message": "real-stage results cannot remain exploratory/failed for final delivery."})
        if result.get("quality_level") in {"heuristic_feasible", "evaluated_best", "approximate", "simulation_estimate"} and isinstance(diag, dict) and diag.get("constraints_checked") is not True:
            warnings.append({"code": "CONSTRAINTS_NOT_EXPLICITLY_CHECKED", "message": "Non-certified results should set diagnostics.constraints_checked=true after feasibility checks."})
        if isinstance(diag, dict) and str(diag.get("fallback_used")).lower() == "true" and result.get("quality_level") in {"global_optimal", "certified_optimal"}:
            failures.append({"code": "FALLBACK_WITH_STRONG_OPTIMALITY", "message": "fallback_used=true cannot support global/certified optimality"})
        if isinstance(diag, dict) and not diag.get("independent_verification") and result.get("quality_level") in {"evaluated_best", "certified_optimal", "global_optimal"}:
            warnings.append({"code": "HIGH_QUALITY_WITHOUT_INDEPENDENT_VERIFICATION", "message": "high quality claims require independent verification artifact"})
        if isinstance(diag, dict) and diag.get("sampling_based") and not diag.get("convergence_check"):
            warnings.append({"code": "SAMPLING_WITHOUT_CONVERGENCE", "message": "sampling/simulation/ray tracing result should include convergence_check"})
        return {"gate": "solver-verify", "status": status_from(failures, warnings), "failures": failures, "warnings": warnings, "result_path": str(result_path), "strict": False, "strict_schema": False}

    schema_failures, schema_report = _schema_failures(result, root=root)
    failures.extend(schema_failures)
    failures.extend(validate_quality_claim(result))

    diag = result.get("diagnostics", {}) or {}
    if not isinstance(diag, dict):
        failures.append({"code": "DIAGNOSTICS_NOT_OBJECT"})
        diag = {}

    if result.get("scope") != "real":
        failures.append({"code": "SCOPE_NOT_REAL", "value": result.get("scope"), "message": "strict final solver results must use scope=real."})
    if result.get("data_source") == "demo_data":
        failures.append({"code": "DEMO_DATA_BLOCKED", "message": "data_source=demo_data cannot enter final outputs."})
    if result.get("solver_status") in TERMINAL_BAD_STATUSES:
        failures.append({"code": "SOLVER_STATUS_BLOCKED", "value": result.get("solver_status")})
    if result.get("violation_count") != 0:
        failures.append({"code": "VIOLATION_COUNT_NOT_ZERO", "value": result.get("violation_count")})
    if diag.get("constraints_checked") is not True:
        failures.append({"code": "CONSTRAINTS_NOT_CHECKED", "message": "diagnostics.constraints_checked must be true."})
    validators = diag.get("domain_validators_run")
    if not isinstance(validators, list) or len(validators) == 0:
        failures.append({"code": "DOMAIN_VALIDATORS_EMPTY", "message": "diagnostics.domain_validators_run must contain at least one validator id."})
    if diag.get("fallback_used") is True and result.get("optimal") is True:
        failures.append({"code": "FALLBACK_CANNOT_BE_OPTIMAL", "message": "fallback_used=true cannot support optimal=true."})
    if result.get("quality_level") in NON_CERTIFIED_OPTIMAL_TRUE and result.get("optimal") is True:
        failures.append({"code": "NON_CERTIFIED_QUALITY_CANNOT_BE_OPTIMAL", "quality_level": result.get("quality_level")})
    if not isinstance(result.get("metrics"), dict) or len(result.get("metrics") or {}) == 0:
        warnings.append({"code": "METRICS_EMPTY", "message": "metrics is empty; final gate may upgrade this to blocking."})

    artifacts = result.get("artifacts") or []
    if not isinstance(artifacts, list):
        failures.append({"code": "ARTIFACTS_NOT_ARRAY"})
        artifacts = []
    if not artifacts:
        failures.append({"code": "ARTIFACTS_EMPTY", "message": "strict solver results must list produced artifact paths."})
    for artifact in artifacts:
        if not isinstance(artifact, str) or not artifact.strip():
            failures.append({"code": "ARTIFACT_PATH_INVALID", "artifact": artifact})
            continue
        resolved = resolve_artifact_path(case_dir, result_path, artifact)
        if not resolved.exists():
            failures.append({"code": "ARTIFACT_NOT_FOUND", "artifact": artifact, "resolved_path": str(resolved)})

    if not str(result.get("limitations", "")).strip():
        failures.append({"code": "LIMITATIONS_EMPTY"})

    report = {
        "gate": "solver-verify",
        "status": status_from(failures, warnings),
        "failures": failures,
        "warnings": warnings,
        "result_path": str(result_path),
        "case_dir": str(case_dir) if case_dir else None,
        "strict": True,
        "strict_schema": bool(strict_schema),
        "schema": schema_report,
    }
    return report


def verify_solver_results(case_dir: Path, *, strict: bool = False, explicit_result: str | None = None, root: Path | None = None) -> dict:
    paths = solution_paths(case_dir, explicit=explicit_result)
    reports = [verify_solver_result(p, case_dir=case_dir, strict=strict, strict_schema=strict, root=root) for p in paths]
    failures: list[dict] = []
    warnings: list[dict] = []
    if not reports:
        failures.append({"code": "NO_SOLUTION_RESULTS_FOUND", "message": "No solution_real.json files were found."})
    for r in reports:
        if r.get("status") == "failed":
            failures.append({"code": "SOLVER_VERIFY_FAILED", "result_path": r.get("result_path"), "failures": r.get("failures", [])})
        elif r.get("status") == "warning":
            warnings.append({"code": "SOLVER_VERIFY_WARNING", "result_path": r.get("result_path"), "warnings": r.get("warnings", [])})
    return {
        "gate": "solver-verify-all",
        "status": status_from(failures, warnings),
        "case_dir": str(Path(case_dir).resolve()),
        "result_count": len(reports),
        "reports": reports,
        "failures": failures,
        "warnings": warnings,
        "strict": strict,
    }
