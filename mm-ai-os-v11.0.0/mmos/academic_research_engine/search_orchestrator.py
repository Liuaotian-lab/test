"""Academic Search Orchestrator — v7.1.

Builds evidence-backed, purpose-layered academic search plans from the v7.1 Problem
Understanding Engine. It still does not fabricate search results: WebSearch / library search
must be executed by an Agent or external search executor and written back to search_results.json.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import read_json, write_json
from mmos.core.artifacts import read_official_json, write_official_json, write_report_json
from mmos.kernel.events import now_iso
from mmos.problem_understanding import understand_problem, understanding_gate

SCHEMA_VERSION = "7.5.0"
PURPOSES = {"domain_model", "method_algorithm", "solver", "verification", "application_case", "constraint_handling", "data_processing"}


def orchestrate_academic_search(case_dir: Path, question_id: str | None = None, budget: str = "full", strict: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    # Ensure the canonical understanding artifact exists. Do not continue if the gate fails in strict mode.
    gate = understanding_gate(case_dir, question_id=question_id, strict=False)
    if strict and gate.get("status") == "failed":
        raise RuntimeError("understanding-gate failed; revise problem understanding before academic-search.")

    signatures = _load_signatures(case_dir)
    if not signatures.get("questions"):
        # Last attempt: create one from corpus.
        understand_problem(case_dir, question_id=question_id, strict=False)
        signatures = _load_signatures(case_dir)
    if not signatures.get("questions"):
        return _fail("NO_PROBLEM_UNDERSTANDING", "Run problem-understand first.", strict)

    questions = _resolve_questions(case_dir, question_id, signatures)
    searches = []
    failures = 0
    for q in questions:
        qid = q["question_id"]
        result = _search_one_question(qid, q["signature"], budget)
        searches.append(result)
        if result.get("status") == "failed":
            failures += 1

    out = {
        "schema_version": SCHEMA_VERSION,
        "status": "passed" if failures == 0 else "failed",
        "case_id": case_dir.name,
        "timestamp": now_iso(),
        "mode": "planned_search_with_agent_populated_results",
        "understanding_gate_status": gate.get("status"),
        "searches": searches,
        "search_count": len(searches),
        "failure_count": failures,
        "agent_execution_contract": {
            "must_execute_queries": True,
            "must_preserve_query_id": True,
            "must_populate_results_with_sources": True,
            "must_extract_identified_methods_with_evidence_span": True,
            "no_fallback_to_self_knowledge": True,
        },
    }
    out_file = write_official_json(case_dir, "workspace/academic_search/search_results.json", out)
    gate_report = validate_search_plan(out, strict=False)
    write_report_json(case_dir, "quality/search_plan_gate_report.json", gate_report)
    if strict and failures > 0:
        raise RuntimeError("Academic search planning failed; no fallback to AI self-knowledge is permitted.")
    return out


def validate_search_plan(search_data_or_case: dict[str, Any] | Path, strict: bool = True) -> dict[str, Any]:
    """Validate that the search plan covers every task with required purposes."""
    if isinstance(search_data_or_case, (str, Path)):
        case_dir = Path(search_data_or_case).resolve()
        data = read_official_json(case_dir, "workspace/academic_search/search_results.json", {}) or {}
    else:
        data = search_data_or_case
        case_dir = None
    issues: list[dict[str, Any]] = []
    for search in data.get("searches", []):
        qid = search.get("question_id", "UNKNOWN")
        queries = search.get("queries", [])
        ids = set()
        purposes = set()
        for i, q in enumerate(queries):
            query_id = q.get("query_id")
            if not query_id:
                issues.append(_issue("critical", "missing_query_id", f"{qid}: query[{i}] missing query_id."))
            elif query_id in ids:
                issues.append(_issue("critical", "duplicate_query_id", f"{qid}: duplicate query_id {query_id}."))
            ids.add(query_id)
            if not q.get("query"):
                issues.append(_issue("critical", "missing_query_text", f"{qid}: query[{i}] missing query text."))
            purpose = q.get("purpose") or q.get("type")
            if purpose not in PURPOSES:
                issues.append(_issue("warning", "unknown_query_purpose", f"{qid}: query[{i}] has unknown purpose {purpose}."))
            else:
                purposes.add(purpose)
            if not q.get("evidence_ids"):
                issues.append(_issue("warning", "query_without_evidence", f"{qid}: query[{i}] has no evidence_ids."))
            if len(str(q.get("query", "")).split()) < 2:
                issues.append(_issue("warning", "query_too_short", f"{qid}: query[{i}] is too short."))
        if queries and "domain_model" not in purposes:
            issues.append(_issue("warning", "missing_domain_model_query", f"{qid}: no domain_model query."))
        if queries and "verification" not in purposes:
            issues.append(_issue("warning", "missing_verification_query", f"{qid}: no verification query."))
        if search.get("requires_optimization") and "constraint_handling" not in purposes and "solver" not in purposes:
            issues.append(_issue("warning", "missing_optimization_solver_query", f"{qid}: optimization detected but no solver/constraint query."))
    status = "failed" if any(i["severity"] == "critical" for i in issues) else ("warning" if issues else "passed")
    report = {
        "schema_version": SCHEMA_VERSION,
        "gate": "search_plan_gate",
        "status": status,
        "issue_count": len(issues),
        "issues": issues,
        "next_action": "execute_web_or_library_search" if status in {"passed", "warning"} else "revise_search_plan",
        "policy": {
            "layered_query_purposes_required": True,
            "query_id_required": True,
            "evidence_backed_query_required": True,
            "no_search_results_are_fabricated": True,
        },
    }
    if case_dir is not None:
        write_report_json(case_dir, "quality/search_plan_gate_report.json", report)
    if strict and status == "failed":
        raise RuntimeError("search-plan-gate failed")
    return report


def _load_signatures(case_dir: Path) -> dict[str, Any]:
    final = read_official_json(case_dir, "workspace/problem_understanding/final_problem_signature.json", {}) or {}
    if final.get("questions"):
        return final
    compat = read_official_json(case_dir, "workspace/problem_signatures/case.signatures.json", {}) or {}
    return compat


def _fail(code: str, message: str, strict: bool) -> dict[str, Any]:
    result = {"status": "failed", "code": code, "message": message}
    if strict:
        raise RuntimeError(f"[{code}] {message}")
    return result


def _resolve_questions(case_dir: Path, question_id: str | None, signatures: dict[str, Any]) -> list[dict[str, Any]]:
    qs = signatures.get("questions", {})
    if question_id:
        q_info = qs.get(question_id)
        if not q_info:
            raise RuntimeError(f"Question {question_id} not found in signatures.")
        return [{"question_id": question_id, "signature": q_info}]
    reg = read_json(case_dir / "registry" / "questions_registry.json", {"questions": []}) or {"questions": []}
    out = []
    for q in reg.get("questions", []):
        qid = q.get("question_id") or q.get("id")
        if qid and q.get("required", True) is not False and qid in qs:
            out.append({"question_id": qid, "signature": qs[qid]})
    return out or [{"question_id": qid, "signature": sig} for qid, sig in qs.items()]


def _search_one_question(qid: str, signature: dict[str, Any], budget: str) -> dict[str, Any]:
    queries = _build_search_queries(signature, budget, qid)
    if not queries:
        return {"question_id": qid, "status": "failed", "queries": [], "total_queries": 0, "results": [], "code": "NO_QUERIES"}
    requires_optimization = any(t.get("task") == "constrained_optimization" for t in signature.get("task_archetypes", []))
    return {
        "question_id": qid,
        "status": "planned",
        "queries": queries,
        "total_queries": len(queries),
        "requires_optimization": requires_optimization,
        "results": [],
        "result_schema_hint": {
            "required_fields": ["source_id", "title", "url_or_doi_or_identifier", "snippet", "query_id", "identified_methods"],
            "identified_method_required_fields": ["method_name", "role", "evidence_span", "relevance_score"],
        },
        "note": "Agent or external search executor must execute queries and populate results; this planner never fabricates sources.",
    }


def _build_search_queries(signature: dict[str, Any], budget: str, qid: str = "Q") -> list[dict[str, Any]]:
    max_queries = {"fast": 3, "regression": 6, "full": 12}.get(budget, 6)
    queries: list[dict[str, Any]] = []
    counter = 0

    def add(purpose: str, query: str, reason: str, evidence_ids: list[str] | None = None, required: bool = False, priority: float = 0.5):
        nonlocal counter
        if not query or any(q["query"].lower() == query.lower() for q in queries):
            return
        counter += 1
        queries.append({
            "query_id": f"{qid}.{purpose}.{counter:03d}",
            "query": query,
            "purpose": purpose,
            "reason": reason,
            "priority": round(float(priority), 3),
            "required": bool(required),
            "evidence_ids": evidence_ids or _signature_evidence(signature),
        })

    domain = (signature.get("domain_family") or {}).get("primary", "unknown")
    for item in _domain_to_queries(domain):
        add(item["purpose"], item["query"], f"Domain query for {domain}.", _signature_evidence(signature), item.get("required", False), item.get("priority", 0.7))

    tasks = [t.get("task") for t in signature.get("task_archetypes", []) if t.get("task")]
    for task in tasks:
        if task == "constrained_optimization":
            add("solver", "constrained optimization numerical methods feasibility sensitivity analysis", "Optimization task requires solver and feasibility evidence.", _task_evidence(signature, task), True, 0.86)
            add("constraint_handling", "constraint handling mathematical modeling penalty method interior point SLSQP", "Optimization task requires constraint handling evidence.", _task_evidence(signature, task), True, 0.84)
        elif task == "prediction":
            add("method_algorithm", "time series prediction regression forecasting model validation", "Prediction task requires predictive modeling methods.", _task_evidence(signature, task), True, 0.82)
            add("verification", "prediction model validation error metrics residual analysis", "Prediction task requires validation metrics.", _task_evidence(signature, task), True, 0.78)
        elif task == "mechanistic_modeling":
            add("method_algorithm", "mechanistic mathematical modeling governing equations parameter estimation", "Mechanistic task requires governing equation search.", _task_evidence(signature, task), True, 0.80)
        elif task == "evaluation":
            add("method_algorithm", "multi criteria decision analysis weighting TOPSIS AHP entropy method", "Evaluation task requires indicator and weighting methods.", _task_evidence(signature, task), True, 0.79)
        elif task == "simulation":
            add("method_algorithm", "Monte Carlo simulation stochastic modeling uncertainty quantification", "Simulation task requires stochastic modeling evidence.", _task_evidence(signature, task), True, 0.77)
        elif task == "parameter_estimation":
            add("method_algorithm", "parameter estimation inverse problem nonlinear least squares calibration", "Parameter estimation task requires fitting and inverse method evidence.", _task_evidence(signature, task), True, 0.78)

    quantities = signature.get("physical_quantities") or []
    if len(quantities) >= 2:
        add("domain_model", f"{' '.join(quantities[:4])} governing equation mathematical model", "Physical quantities suggest governing-equation search.", _signature_evidence(signature), False, 0.66)

    constraints = signature.get("constraints") or []
    if constraints:
        c_text = " ".join([c.get("text", str(c)) if isinstance(c, dict) else str(c) for c in constraints[:3]])
        add("constraint_handling", f"{c_text} constrained optimization modeling method", "Explicit constraints require constraint-handling search.", _constraint_evidence(constraints), True, 0.82)

    add("verification", "mathematical modeling validation sensitivity analysis robustness check", "Every method plan needs validation and robustness evidence.", _signature_evidence(signature), True, 0.62)
    add("application_case", f"{domain.replace('_', ' ').replace('.', ' ')} mathematical modeling application case", "Application cases help calibrate modeling assumptions.", _signature_evidence(signature), False, 0.48)

    return sorted(queries, key=lambda x: x.get("priority", 0), reverse=True)[:max_queries]


def _signature_evidence(signature: dict[str, Any]) -> list[str]:
    ids = []
    if signature.get("source_evidence_ids"):
        ids.extend(signature.get("source_evidence_ids")[:3])
    df = signature.get("domain_family") or {}
    ids.extend(df.get("evidence_ids") or [])
    for t in signature.get("task_archetypes", [])[:2]:
        ids.extend(t.get("evidence_ids") or [])
    return _dedup(ids)[:5]


def _task_evidence(signature: dict[str, Any], task_name: str) -> list[str]:
    ids = []
    for t in signature.get("task_archetypes", []):
        if t.get("task") == task_name:
            ids.extend(t.get("evidence_ids") or [])
    return _dedup(ids or _signature_evidence(signature))[:5]


def _constraint_evidence(constraints: list[Any]) -> list[str]:
    ids = []
    for c in constraints:
        if isinstance(c, dict):
            ids.extend(c.get("evidence_ids") or [])
    return _dedup(ids)[:5]


def _dedup(items: list[Any]) -> list[Any]:
    out = []
    for x in items:
        if x and x not in out:
            out.append(x)
    return out


def _domain_to_queries(domain: str) -> list[dict[str, Any]]:
    templates = {
        "physical_process.thermal_process": [
            {"query": "reflow soldering thermal profile heat transfer mathematical model", "purpose": "domain_model", "required": True, "priority": 0.90},
            {"query": "thermal process parameter estimation inverse problem optimization", "purpose": "method_algorithm", "priority": 0.78},
            {"query": "heat transfer model validation residual sensitivity analysis", "purpose": "verification", "priority": 0.68},
        ],
        "physical_process.hydraulic_pressure_control": [
            {"query": "high pressure fuel pipe compressible flow mathematical model", "purpose": "domain_model", "required": True, "priority": 0.90},
            {"query": "hydraulic pressure control valve optimization ODE parameter estimation", "purpose": "method_algorithm", "priority": 0.76},
        ],
        "graph_network.graph_theory": [
            {"query": "graph theory network flow optimization mathematical model", "purpose": "domain_model", "required": True, "priority": 0.88},
            {"query": "shortest path maximum flow minimum cut algorithm complexity", "purpose": "solver", "priority": 0.80},
        ],
        "traffic_flow": [
            {"query": "traffic flow prediction mathematical model time series network", "purpose": "domain_model", "required": True, "priority": 0.88},
            {"query": "traffic forecasting validation error metrics congestion prediction", "purpose": "verification", "priority": 0.72},
        ],
        "statistical_decision": [
            {"query": "multi criteria decision analysis evaluation ranking mathematical modeling", "purpose": "domain_model", "required": True, "priority": 0.86},
            {"query": "entropy weight TOPSIS AHP robustness sensitivity analysis", "purpose": "verification", "priority": 0.75},
        ],
        "stochastic_simulation": [
            {"query": "Monte Carlo simulation stochastic process uncertainty quantification mathematical model", "purpose": "domain_model", "required": True, "priority": 0.85},
            {"query": "simulation model validation confidence interval variance reduction", "purpose": "verification", "priority": 0.72},
        ],
        "solar_optical.heliostat_field": [
            {"query": "heliostat field layout optimization optical efficiency mathematical model", "purpose": "domain_model", "required": True, "priority": 0.88},
            {"query": "solar tower ray tracing cosine efficiency atmospheric attenuation validation", "purpose": "verification", "priority": 0.73},
        ],
    }
    return templates.get(domain, [
        {"query": f"{domain.replace('_', ' ').replace('.', ' ')} mathematical modeling methods", "purpose": "domain_model", "required": True, "priority": 0.64},
        {"query": f"{domain.replace('_', ' ').replace('.', ' ')} validation robustness sensitivity analysis", "purpose": "verification", "priority": 0.55},
    ])


def _issue(severity: str, typ: str, message: str) -> dict[str, Any]:
    return {"severity": severity, "type": typ, "message": message}
