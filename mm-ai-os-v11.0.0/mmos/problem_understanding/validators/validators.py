from __future__ import annotations
from typing import Any

CRITICAL_CLAIM_FIELDS = ["goal", "task_archetypes", "variables", "constraints", "data_requirements", "required_outputs", "dependencies"]


def validate_problem_understanding(signature: dict[str, Any], evidence_index: dict[str, Any], strict: bool = True) -> dict[str, Any]:
    """Run deterministic validators over a candidate or final problem signature."""
    evidence_ids = {b.get("evidence_id") for b in evidence_index.get("evidence_blocks", []) if b.get("evidence_id")}
    issues: list[dict[str, Any]] = []
    questions = signature.get("questions", {}) if isinstance(signature, dict) else {}
    if not questions:
        issues.append(_issue("critical", "missing_questions", "Signature does not contain any questions."))
    for qid, q in questions.items():
        _validate_question(qid, q or {}, evidence_ids, issues)
    status = _status_from_issues(issues, strict)
    return {
        "validator": "problem_understanding_validators",
        "status": status,
        "issue_count": len(issues),
        "blocking_issue_count": len([i for i in issues if i["severity"] == "critical"]),
        "issues": issues,
        "checks": {
            "schema_shape": "passed" if questions else "failed",
            "evidence_references": "passed" if not [i for i in issues if i["type"].startswith("evidence_")] else "failed",
            "task_readiness": "passed" if not [i for i in issues if i["type"].startswith("readiness_")] else "warning",
        },
    }


def _validate_question(qid: str, q: dict[str, Any], evidence_ids: set[str], issues: list[dict[str, Any]]) -> None:
    if not (q.get("goal") or {}).get("claim"):
        issues.append(_issue("critical", "missing_goal", f"{qid}: missing problem goal."))
    _require_evidence(qid, "goal", q.get("goal"), evidence_ids, issues, critical=True)

    tasks = q.get("task_archetypes") or []
    if not tasks:
        issues.append(_issue("critical", "missing_tasks", f"{qid}: no task_archetypes extracted."))
    for i, task in enumerate(tasks):
        if not task.get("task"):
            issues.append(_issue("critical", "missing_task_name", f"{qid}: task_archetypes[{i}] missing task."))
        _require_evidence(qid, f"task_archetypes[{i}]", task, evidence_ids, issues, critical=True)
        _confidence(qid, f"task_archetypes[{i}]", task, issues)

    variables = q.get("variables") or []
    for i, var in enumerate(variables):
        if not var.get("name"):
            issues.append(_issue("critical", "missing_variable_name", f"{qid}: variables[{i}] missing name."))
        if not var.get("role"):
            issues.append(_issue("warning", "missing_variable_role", f"{qid}: variables[{i}] missing role."))
        _require_evidence(qid, f"variables[{i}]", var, evidence_ids, issues, critical=True)
        _confidence(qid, f"variables[{i}]", var, issues)

    for i, cons in enumerate(q.get("constraints") or []):
        if not cons.get("text"):
            issues.append(_issue("critical", "missing_constraint_text", f"{qid}: constraints[{i}] missing text."))
        if not cons.get("direction"):
            issues.append(_issue("warning", "missing_constraint_direction", f"{qid}: constraints[{i}] missing direction."))
        _require_evidence(qid, f"constraints[{i}]", cons, evidence_ids, issues, critical=True)

    for key in ["data_requirements", "required_outputs", "dependencies"]:
        for i, item in enumerate(q.get(key) or []):
            _require_evidence(qid, f"{key}[{i}]", item, evidence_ids, issues, critical=(key != "dependencies"))
            _confidence(qid, f"{key}[{i}]", item, issues)

    task_names = {t.get("task") for t in tasks}
    var_roles = " ".join(str(v.get("role", "")) for v in variables).lower()
    if "constrained_optimization" in task_names and variables and "decision" not in var_roles and "objective" not in var_roles:
        issues.append(_issue("warning", "readiness_optimization_without_decision_variable", f"{qid}: optimization detected but no decision/objective variable role found."))
    if "prediction" in task_names and variables and "target" not in var_roles and "state" not in var_roles:
        issues.append(_issue("warning", "readiness_prediction_without_target", f"{qid}: prediction detected but no target/state variable role found."))
    if "evaluation" in task_names and not any(v.get("role") == "evaluation_indicator" for v in variables):
        issues.append(_issue("warning", "readiness_evaluation_without_indicators", f"{qid}: evaluation detected but no indicator variable found."))


def _require_evidence(qid: str, field: str, obj: Any, evidence_ids: set[str], issues: list[dict[str, Any]], critical: bool) -> None:
    if not isinstance(obj, dict):
        return
    ids = obj.get("evidence_ids") or []
    if not ids:
        issues.append(_issue("critical" if critical else "warning", "evidence_missing", f"{qid}: {field} has no evidence_ids."))
        return
    bad = [e for e in ids if e not in evidence_ids]
    if bad:
        issues.append(_issue("critical", "evidence_unknown", f"{qid}: {field} cites unknown evidence ids: {bad}."))


def _confidence(qid: str, field: str, obj: Any, issues: list[dict[str, Any]]) -> None:
    if not isinstance(obj, dict) or "confidence" not in obj:
        return
    try:
        v = float(obj.get("confidence"))
    except Exception:
        issues.append(_issue("warning", "confidence_not_numeric", f"{qid}: {field} confidence is not numeric."))
        return
    if not (0 <= v <= 1):
        issues.append(_issue("critical", "confidence_out_of_range", f"{qid}: {field} confidence {v} is outside [0, 1]."))


def _status_from_issues(issues: list[dict[str, Any]], strict: bool) -> str:
    if any(i["severity"] == "critical" for i in issues):
        return "failed"
    if issues:
        return "failed" if strict else "warning"
    return "passed"


def _issue(severity: str, typ: str, message: str) -> dict[str, Any]:
    return {"severity": severity, "type": typ, "message": message}
