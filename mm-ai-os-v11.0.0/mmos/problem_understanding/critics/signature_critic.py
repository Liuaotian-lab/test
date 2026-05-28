from __future__ import annotations
from typing import Any
import re

CONSTRAINT_WORDS = re.compile(r"不超过|不得超过|不少于|至少|至多|约束|限制|必须|不能|上限|下限|低于|高于")
DATA_WORDS = re.compile(r"附件|数据|表格|表\s*\d*|图\s*\d*|曲线|Excel|xlsx|CSV|csv", re.IGNORECASE)
OPT_WORDS = re.compile(r"优化|最优|最大|最小|optimal|optimization|minimize|maximize", re.IGNORECASE)
PRED_WORDS = re.compile(r"预测|预报|未来|forecast|predict|prediction", re.IGNORECASE)


def critique_signature(signature: dict[str, Any], evidence_index: dict[str, Any]) -> dict[str, Any]:
    """Find likely omissions and overclaims. This is a deterministic critic.

    It complements, but does not replace, external AI critic review.
    """
    issues: list[dict[str, Any]] = []
    evidence_by_q: dict[str, str] = {}
    for b in evidence_index.get("evidence_blocks", []):
        qid = b.get("question_id") or "GLOBAL"
        evidence_by_q.setdefault(qid, "")
        evidence_by_q[qid] += "\n" + b.get("text", "")
    for qid, q in (signature.get("questions") or {}).items():
        text = evidence_by_q.get(qid, "") + "\n" + evidence_by_q.get("GLOBAL", "")
        tasks = {t.get("task") for t in q.get("task_archetypes", [])}
        constraints = q.get("constraints") or []
        if CONSTRAINT_WORDS.search(text) and not constraints:
            issues.append(_issue("high", "missing_constraint", qid, "Evidence contains constraint markers but constraints is empty."))
        if DATA_WORDS.search(text) and not (q.get("data_requirements") or []):
            issues.append(_issue("medium", "missing_data_requirement", qid, "Evidence mentions data/table/figure/attachment but data_requirements is empty."))
        if OPT_WORDS.search(text) and "constrained_optimization" not in tasks:
            issues.append(_issue("medium", "possible_missing_optimization_task", qid, "Evidence contains optimization markers but optimization task was not extracted."))
        if PRED_WORDS.search(text) and "prediction" not in tasks:
            issues.append(_issue("medium", "possible_missing_prediction_task", qid, "Evidence contains prediction markers but prediction task was not extracted."))
        for t in q.get("task_archetypes", []):
            if float(t.get("confidence", 0)) > 0.85 and len(t.get("evidence_ids") or []) < 1:
                issues.append(_issue("medium", "overconfident_without_evidence", qid, f"Task {t.get('task')} is high confidence but has insufficient evidence."))
        if q.get("domain_family", {}).get("primary") == "unknown":
            issues.append(_issue("medium", "unknown_domain", qid, "Domain is unknown; external Agent review recommended."))
    status = "needs_revision" if any(i["severity"] == "high" for i in issues) else ("warning" if issues else "passed")
    return {
        "critic": "deterministic_signature_critic",
        "status": status,
        "issue_count": len(issues),
        "issues": issues,
        "note": "External AI critic may add semantic issues that deterministic rules cannot see.",
    }


def _issue(severity: str, typ: str, qid: str, message: str) -> dict[str, Any]:
    return {"severity": severity, "type": typ, "question_id": qid, "message": message}
