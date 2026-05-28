from __future__ import annotations

from pathlib import Path
from shutil import copy2
from typing import Any

from mmos.academic_research_engine.search_orchestrator import orchestrate_academic_search
from mmos.contracts.manager import ensure_case_scaffold, activate_question
from mmos.core.artifacts import read_official_json, write_official_json
from mmos.kernel.events import now_iso
from mmos.kernel.hashing import sha256_file
from mmos.kernel.jsonio import read_json, write_json

SCHEMA_VERSION = "7.5.0"
FIXTURE_NAME = "thermal_optimization_minimal"


def repo_root_from_case(case_dir: Path) -> Path:
    p = Path(case_dir).resolve()
    for parent in [p, *p.parents]:
        if (parent / "mmos").exists() and (parent / "tests" / "fixtures" / "synthetic_cases").exists():
            return parent
    return Path.cwd().resolve()


def fixture_root(repo_root: Path) -> Path:
    return Path(repo_root) / "tests" / "fixtures" / "synthetic_cases" / FIXTURE_NAME


def install_synthetic_raw(case_dir: Path, *, overwrite: bool = True) -> dict[str, Any]:
    """Install the deterministic v7.5 raw problem files into an existing case."""
    case_dir = Path(case_dir).resolve()
    ensure_case_scaffold(case_dir)
    root = repo_root_from_case(case_dir)
    src_dir = fixture_root(root) / "raw"
    if not src_dir.exists():
        raise FileNotFoundError(f"synthetic fixture raw directory not found: {src_dir}")
    copied: list[dict[str, Any]] = []
    dst_dir = case_dir / "data" / "raw"
    dst_dir.mkdir(parents=True, exist_ok=True)
    for src in sorted(src_dir.iterdir()):
        if not src.is_file():
            continue
        dst = dst_dir / src.name
        if dst.exists() and not overwrite:
            copied.append({"path": str(dst.relative_to(case_dir)), "action": "kept"})
            continue
        copy2(src, dst)
        copied.append({
            "path": str(dst.relative_to(case_dir)),
            "action": "copied",
            "sha256": sha256_file(dst),
            "size_bytes": dst.stat().st_size,
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed",
        "case_id": case_dir.name,
        "fixture": FIXTURE_NAME,
        "copied": copied,
        "timestamp": now_iso(),
    }


def inject_synthetic_search_results(case_dir: Path, *, question_id: str | None = None) -> dict[str, Any]:
    """Populate planned academic searches with deterministic source-backed methods.

    This is not a real literature search. It is a fixture used only for regression
    tests so the full pipeline can run without external network or LLM access.
    """
    case_dir = Path(case_dir).resolve()
    ensure_case_scaffold(case_dir)
    search_data = read_official_json(case_dir, "workspace/academic_search/search_results.json", {}) or {}
    if not search_data.get("searches"):
        search_data = orchestrate_academic_search(case_dir, question_id=question_id, budget="regression", strict=False)
    searches = []
    for search in search_data.get("searches", []):
        qid = search.get("question_id")
        if question_id and qid != question_id:
            searches.append(search)
            continue
        queries = search.get("queries", [])
        first_query = queries[0] if queries else {"query_id": f"{qid}.fixture.001", "query": "thermal model calibration"}
        second_query = queries[1] if len(queries) > 1 else first_query
        third_query = queries[2] if len(queries) > 2 else first_query
        search = dict(search)
        search["status"] = "fixture_results_injected"
        search["results"] = [
            {
                "source_id": f"SRC-{qid}-THERMAL-001",
                "query_id": first_query.get("query_id"),
                "title": "Lumped-parameter heat transfer models for thermal process control",
                "url": "https://example.org/synthetic/thermal-lumped-model",
                "snippet": "Lumped thermal capacitance models support temperature prediction, parameter calibration and residual validation in controlled heating processes.",
                "identified_methods": [
                    _method("lumped_parameter_heat_transfer_model", "primary_model", "Models device temperature as a first-order thermal process driven by heating power and loss to ambient air.", 0.94, "Lumped-parameter heat transfer models for thermal process control", "https://example.org/synthetic/thermal-lumped-model"),
                    _method("nonlinear_least_squares_parameter_estimation", "model", "Fits thermal resistance and capacitance parameters by minimizing residual errors against observations.", 0.88, "Lumped-parameter heat transfer models for thermal process control", "https://example.org/synthetic/thermal-lumped-model"),
                ],
            },
            {
                "source_id": f"SRC-{qid}-OPT-002",
                "query_id": second_query.get("query_id"),
                "title": "Constrained numerical optimization for process parameter tuning",
                "url": "https://example.org/synthetic/constrained-process-optimization",
                "snippet": "Sequential quadratic programming and grid-refined feasible search are standard approaches for bounded process optimization with temperature constraints.",
                "identified_methods": [
                    _method("grid_refined_feasible_search", "model", "Uses a bounded grid to cross-check feasible control settings and provide a robust alternative model family.", 0.83, "Constrained numerical optimization for process parameter tuning", "https://example.org/synthetic/constrained-process-optimization"),
                    _method("sequential_quadratic_programming", "optimization", "Solves the bounded energy minimization problem while enforcing terminal temperature and maximum temperature constraints.", 0.91, "Constrained numerical optimization for process parameter tuning", "https://example.org/synthetic/constrained-process-optimization"),
                ],
            },
            {
                "source_id": f"SRC-{qid}-VALID-003",
                "query_id": third_query.get("query_id"),
                "title": "Residual validation and sensitivity analysis for thermal prediction models",
                "url": "https://example.org/synthetic/thermal-validation-sensitivity",
                "snippet": "Residual MAE, terminal-temperature error, perturbation sensitivity and independent reduced-model checks are useful validation evidence for thermal modeling.",
                "identified_methods": [
                    _method("piecewise_linear_response_model", "model", "Provides an interpretable alternative prediction model for tournament comparison.", 0.81, "Residual validation and sensitivity analysis for thermal prediction models", "https://example.org/synthetic/thermal-validation-sensitivity"),
                    _method("residual_and_sensitivity_validation", "verification", "Checks residual error, terminal-temperature agreement and parameter perturbation robustness.", 0.93, "Residual validation and sensitivity analysis for thermal prediction models", "https://example.org/synthetic/thermal-validation-sensitivity"),
                ],
            },
        ]
        search["fixture_note"] = "Deterministic v7.5 synthetic search results; not real literature search."
        searches.append(search)
    search_data = dict(search_data)
    search_data["schema_version"] = SCHEMA_VERSION
    search_data["status"] = "passed"
    search_data["fixture"] = FIXTURE_NAME
    search_data["searches"] = searches
    search_data["timestamp"] = now_iso()
    write_official_json(case_dir, "workspace/academic_search/search_results.json", search_data)
    return {"schema_version": SCHEMA_VERSION, "status": "passed", "case_id": case_dir.name, "search_count": len(searches), "search_results": "workspace/academic_search/official/search_results.json"}


def _method(method_name: str, role: str, description: str, relevance: float, title: str, url: str) -> dict[str, Any]:
    return {
        "method_name": method_name,
        "name": method_name,
        "role": role,
        "description": description,
        "evidence_span": description,
        "relevance_score": relevance,
        "source_title": title,
        "source_url": url,
        "source_snippet": description,
    }


def inject_synthetic_solution(case_dir: Path, *, question_id: str = "Q1") -> dict[str, Any]:
    """Inject deterministic solver, contract, report and output artifacts for e2e tests."""
    case_dir = Path(case_dir).resolve()
    ensure_case_scaffold(case_dir)
    activate_question(case_dir, question_id, qtype="generic_optimization", title="Thermal control optimization", required=True, force=False)
    _refine_contracts(case_dir, question_id)
    _write_solution_artifacts(case_dir, question_id)
    _write_report(case_dir, question_id)
    _write_output_registry(case_dir, question_id)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed",
        "case_id": case_dir.name,
        "question_id": question_id,
        "solution": f"results/{question_id}/outputs/solution_real.json",
        "report": f"reports/{question_id}_thermal_report.md",
        "outputs_registry": "registry/outputs_registry.json",
    }


def _refine_contracts(case_dir: Path, qid: str) -> None:
    qdir = case_dir / "contracts" / "questions" / qid
    qdir.mkdir(parents=True, exist_ok=True)
    write_json(qdir / "problem_spec.json", {
        "question_id": qid,
        "description": "Fit a thermal prediction model and optimize bounded control parameters for minimum energy while satisfying terminal and maximum temperature constraints.",
        "source_excerpt": "Thermal prediction, bounded control optimization, residual validation and sensitivity analysis.",
    })
    write_json(qdir / "variable_registry.json", {
        "question_id": qid,
        "variables": [
            {"name": "time_t", "role": "independent_variable", "unit": "min"},
            {"name": "heating_power_P", "role": "control", "unit": "W"},
            {"name": "belt_speed_v", "role": "decision_variable", "unit": "m/min"},
            {"name": "temperature_T", "role": "state", "unit": "degC"},
        ],
    })
    write_json(qdir / "constraint_registry.json", {
        "question_id": qid,
        "constraints": [
            {"name": "speed_bounds", "expression": "0.5 <= v <= 2.0"},
            {"name": "temperature_cap", "expression": "max(T) <= 250"},
            {"name": "terminal_temperature", "expression": "T_final >= 220"},
        ],
    })
    write_json(qdir / "validation_contract.json", {
        "question_id": qid,
        "validators": [
            {"name": "solver_schema", "type": "json", "target": f"results/{qid}/outputs/solution_real.json"},
            {"name": "constraint_feasibility", "type": "numeric", "target": "diagnostics.constraints_checked"},
            {"name": "report_consistency", "type": "text_numeric", "target": f"reports/{qid}_thermal_report.md"},
        ],
    })
    write_json(qdir / "output_contract.json", {
        "question_id": qid,
        "outputs": [
            {"path": f"results/{qid}/outputs/solution_real.json", "type": "json", "required": True},
            {"path": f"reports/{qid}_thermal_report.md", "type": "markdown", "required": True},
        ],
    })


def _write_solution_artifacts(case_dir: Path, qid: str) -> None:
    out_dir = case_dir / "results" / qid / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    solution = _solution_payload(qid, objective=1810.0, solver_name="reference_thermal_optimizer")
    write_json(out_dir / "solution_real.json", solution)
    write_json(out_dir / "solution_reduced.json", _solution_payload(qid, objective=1810.0, solver_name="reduced_equation_recompute"))
    tdir = case_dir / "results" / qid / "tournament"
    tdir.mkdir(parents=True, exist_ok=True)
    write_json(tdir / "independent_equation_variant.json", _solution_payload(qid, objective=1808.0, solver_name="independent_equation_variant"))
    write_json(tdir / "grid_refinement_variant.json", _solution_payload(qid, objective=1812.0, solver_name="grid_refinement_variant"))


def _solution_payload(qid: str, *, objective: float, solver_name: str) -> dict[str, Any]:
    return {
        "question_id": qid,
        "status": "success",
        "stage": "real",
        "quality_level": "evaluated_best",
        "solver_name": solver_name,
        "method": "lumped_parameter_heat_transfer_with_bounded_optimization",
        "objective_value": objective,
        "diagnostics": {
            "model_level": "L4",
            "constraints_checked": True,
            "feasible": True,
            "max_temperature": 238.6,
            "terminal_temperature": 220.0,
            "optimized_speed": 1.25,
            "independent_verification": {"status": "passed", "relative_difference": 0.0},
            "sensitivity_parameters": ["ambient_temperature", "sensor_noise", "heating_power"],
            "solver_variants": ["reference_thermal_optimizer", "independent_equation_variant", "grid_refinement_variant"],
            "multi_solver": True,
            "constraint_margin": 0.12,
        },
        "comparison_protocol": {
            "same_metric_definition": True,
            "same_sampling_strategy": True,
            "same_domain_scope": True,
            "same_weighting_policy": True,
        },
        "created_at": now_iso(),
    }


def _write_report(case_dir: Path, qid: str) -> None:
    report = f"""# {qid} Thermal Optimization Report

This deterministic synthetic report binds the solver output to the final deliverable.

- objective_value: 1810.0
- The fitted control policy keeps the maximum temperature at 238.6 degrees Celsius and reaches terminal temperature 220.0 degrees Celsius.
- optimized_speed is 1.25 m/min under the bounded feasible search.

The result is supported by residual validation, independent recomputation and sensitivity analysis for ambient temperature, sensor noise and heating power.
"""
    (case_dir / "reports").mkdir(parents=True, exist_ok=True)
    (case_dir / "reports" / f"{qid}_thermal_report.md").write_text(report, encoding="utf-8")


def _write_output_registry(case_dir: Path, qid: str) -> None:
    outputs = []
    for rel, kind, owner in [
        (f"results/{qid}/outputs/solution_real.json", "json", qid),
        (f"reports/{qid}_thermal_report.md", "markdown", qid),
    ]:
        p = case_dir / rel
        outputs.append({
            "path": rel,
            "type": kind,
            "owner_question": owner,
            "required": True,
            "validator": {"required_non_empty": True, "min_chars": 80} if kind == "markdown" else {"required_non_empty": True, "required_fields": ["question_id", "status", "quality_level", "diagnostics"]},
            "sha256": sha256_file(p),
            "freshness_sources": [],
        })
    write_json(case_dir / "registry" / "outputs_registry.json", {"case_id": case_dir.name, "outputs": outputs})


def write_golden_snapshot(case_dir: Path, destination: Path) -> dict[str, Any]:
    """Write stable, timestamp-free golden summaries for fixture maintenance."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "problem_graph.golden.json": _strip_unstable(read_json(case_dir / "workspace" / "problem_graph.json", {}) or {}),
        "search_plan.golden.json": _strip_unstable(read_official_json(case_dir, "workspace/academic_search/search_results.json", {}) or {}),
        "method_plan.golden.json": _strip_unstable(read_official_json(case_dir, "workspace/method_plan/case.method_plan_summary.json", {}) or {}),
        "package_manifest.golden.json": _strip_package(read_json(case_dir / "package" / "package_manifest.json", {}) or {}),
    }
    written = []
    for name, data in artifacts.items():
        write_json(destination / name, data)
        written.append(str(destination / name))
    return {"status": "passed", "written": written}


def _strip_unstable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _strip_unstable(v) for k, v in obj.items() if k not in {"timestamp", "generated_at", "created_at", "approved_at"}}
    if isinstance(obj, list):
        return [_strip_unstable(v) for v in obj]
    return obj


def _strip_package(obj: dict[str, Any]) -> dict[str, Any]:
    if not obj:
        return {}
    return {
        "case_id": obj.get("case_id"),
        "zip_path": obj.get("zip_path"),
        "file_count": len(obj.get("files", [])),
        "final_gate_report": obj.get("final_gate_report"),
        "paths": sorted(f.get("path") for f in obj.get("files", []) if f.get("path")),
    }


def run_synthetic_e2e(case_dir: Path, *, force: bool = False) -> dict[str, Any]:
    """Run the complete deterministic v7.5 synthetic pipeline in one process."""
    import shutil
    from mmos.ingestion.document_ingestor import build_problem_corpus
    from mmos.problem_graph.parser import build_problem_graph
    from mmos.problem_understanding import understand_problem
    from mmos.academic_research_engine.search_orchestrator import validate_search_plan
    from mmos.academic_research_engine.method_matcher import match_methods
    from mmos.academic_research_engine.plan_builder import build_method_plan
    from mmos.academic_research_engine.coverage_checker import check_coverage
    from mmos.academic_research_engine.citation_manager import build_citation_list, validate_citations
    from mmos.method_plan.synthesizer import synthesize_method_plan
    from mmos.artifacts.package import output_build, package_case
    from mmos.gates.final_gate import final_gate_check

    case_dir = Path(case_dir).resolve()
    if case_dir.exists() and force:
        shutil.rmtree(case_dir)
    ensure_case_scaffold(case_dir)
    steps: list[dict[str, Any]] = []

    def step(name: str, fn):
        try:
            result = fn()
            status = result.get("status", "ok") if isinstance(result, dict) else "ok"
            steps.append({"step": name, "status": status, "result": result})
            return result
        except Exception as exc:
            result = {"status": "failed", "error": str(exc)}
            steps.append({"step": name, "status": "failed", "result": result})
            raise

    step("synthetic_install", lambda: install_synthetic_raw(case_dir))
    step("ingest_documents", lambda: build_problem_corpus(case_dir))
    step("problem_parse_v2", lambda: build_problem_graph(case_dir))
    step("problem_understand", lambda: understand_problem(case_dir, strict=False))
    step("academic_search", lambda: orchestrate_academic_search(case_dir, budget="full", strict=False))
    step("search_plan_gate", lambda: validate_search_plan(case_dir, strict=False))
    step("synthetic_search_inject", lambda: inject_synthetic_search_results(case_dir))
    step("method_match", lambda: match_methods(case_dir, strict=False))
    step("method_plan_build", lambda: build_method_plan(case_dir, strict=False))
    step("coverage_gap_analysis", lambda: check_coverage(case_dir, strict=False))
    step("citation_build", lambda: build_citation_list(case_dir))
    step("citation_validate", lambda: validate_citations(case_dir, strict=False))
    step("method_plan_synthesize", lambda: synthesize_method_plan(case_dir, strict=False))
    step("synthetic_solution_inject", lambda: inject_synthetic_solution(case_dir, question_id="Q1"))
    step("output_build", lambda: output_build(case_dir))
    step("final_gate", lambda: final_gate_check(case_dir, strict_warnings=False, write=True))
    step("package_submit", lambda: package_case(case_dir, strict_warnings=False))

    status = "passed" if all(s["status"] in {"passed", "ok", "warning"} for s in steps) and steps[-1]["result"].get("status") == "ok" else "failed"
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "case_id": case_dir.name,
        "fixture": FIXTURE_NAME,
        "step_count": len(steps),
        "steps": [{"step": s["step"], "status": s["status"]} for s in steps],
        "package_manifest": "package/package_manifest.json",
        "final_gate_report": "final_outputs/final_gate_check.json",
        "timestamp": now_iso(),
    }
    write_json(case_dir / "quality" / "synthetic_e2e_report.json", report)
    return report
