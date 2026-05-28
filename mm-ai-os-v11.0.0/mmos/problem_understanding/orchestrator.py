from __future__ import annotations
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import write_json, read_json
from mmos.core.artifacts import read_official_json, write_official_json, write_report_json, official_path, candidate_path
from mmos.kernel.events import now_iso
from .evidence.document_slicer import build_evidence_index
from .ai_extractors.signature_extractor import build_candidate_signature
from .critics.signature_critic import critique_signature
from .validators.validators import validate_problem_understanding
from .adjudication.consensus_builder import choose_final_signature

SCHEMA_VERSION = "7.5.0"


def understand_problem(case_dir: Path, question_id: str | None = None, strict: bool = False) -> dict[str, Any]:
    """Build evidence, candidate signatures, critic review, validators and final signature.

    This is the v7.1 replacement for relying on fixed keyword matching alone. It remains safe
    without an online model because it writes an Agent contract and requires evidence-backed JSON.
    """
    case_dir = Path(case_dir).resolve()
    evidence = build_evidence_index(case_dir, question_id=question_id)
    candidates = build_candidate_signature(case_dir, evidence, question_id=question_id, prefer_agent_file=True)
    final_sig = choose_final_signature(candidates)
    final_sig.setdefault("schema_version", SCHEMA_VERSION)
    final_sig.setdefault("case_id", case_dir.name)
    final_sig.setdefault("timestamp", now_iso())
    final_sig.setdefault("status", "draft")
    final_sig.setdefault("mode", "ai_constrained_understanding_with_deterministic_validation")

    critic = critique_signature(final_sig, evidence)
    validation = validate_problem_understanding(final_sig, evidence, strict=strict)
    gate = _gate_decision(critic, validation, strict=strict)
    final_sig["status"] = gate["status"]
    final_sig["validation_report"] = validation
    final_sig["critic_report"] = critic
    final_sig["gate_summary"] = gate

    base = case_dir / "workspace" / "problem_understanding"
    write_report_json(case_dir, "workspace/problem_understanding/signature_review.json", {"schema_version": SCHEMA_VERSION, "case_id": case_dir.name, "critic": critic, "validation": validation})
    write_official_json(case_dir, "workspace/problem_understanding/final_problem_signature.json", final_sig)
    write_report_json(case_dir, "quality/understanding_gate_report.json", gate)

    # Compatibility artifact for v7.0 academic_research_engine.
    compat = build_compat_signature(final_sig, case_dir.name)
    write_official_json(case_dir, "workspace/problem_signatures/case.signatures.json", compat)

    return {
        "schema_version": SCHEMA_VERSION,
        "status": gate["status"],
        "case_id": case_dir.name,
        "question_id": question_id,
        "evidence_index": str(official_path(case_dir, "workspace/problem_understanding/evidence_index.json").relative_to(case_dir)),
        "candidate_signatures": str(candidate_path(case_dir, "workspace/problem_understanding/candidate_signatures.json").relative_to(case_dir)),
        "final_problem_signature": str(official_path(case_dir, "workspace/problem_understanding/final_problem_signature.json").relative_to(case_dir)),
        "understanding_gate_report": str((case_dir / "workspace" / "problem_understanding" / "reports" / "understanding_gate_report.json").relative_to(case_dir)),
        "gate": gate,
        "note": "External Agent may provide workspace/problem_understanding/candidate/agent_candidate_signature.json for stronger semantic understanding; deterministic validators still apply.",
    }


def understanding_gate(case_dir: Path, question_id: str | None = None, strict: bool = True) -> dict[str, Any]:
    """Evaluate whether problem understanding is safe enough to enter academic search."""
    case_dir = Path(case_dir).resolve()
    final_path = official_path(case_dir, "workspace/problem_understanding/final_problem_signature.json")
    evidence_path = official_path(case_dir, "workspace/problem_understanding/evidence_index.json")
    if not final_path.exists() and not (case_dir / "workspace" / "problem_understanding" / "final_problem_signature.json").exists() or not evidence_path.exists() and not (case_dir / "workspace" / "problem_understanding" / "evidence_index.json").exists():
        return understand_problem(case_dir, question_id=question_id, strict=strict)["gate"]
    final_sig = read_official_json(case_dir, "workspace/problem_understanding/final_problem_signature.json", {}) or {}
    evidence = read_official_json(case_dir, "workspace/problem_understanding/evidence_index.json", {}) or {}
    if question_id:
        final_sig = _filter_question(final_sig, question_id)
    critic = critique_signature(final_sig, evidence)
    validation = validate_problem_understanding(final_sig, evidence, strict=strict)
    gate = _gate_decision(critic, validation, strict=strict)
    write_report_json(case_dir, "quality/understanding_gate_report.json", gate)
    return gate


def build_compat_signature(final_sig: dict[str, Any], case_id: str) -> dict[str, Any]:
    questions = {}
    for qid, q in (final_sig.get("questions") or {}).items():
        questions[qid] = {
            "schema_version": SCHEMA_VERSION,
            "question_id": qid,
            "title": q.get("goal", {}).get("claim", qid)[:80],
            "domain_family": q.get("domain_family") or {"primary": "unknown", "confidence": 0.1, "evidence_terms": []},
            "entities": {"problem_entities": _entities_from_variables(q.get("variables") or [])},
            "physical_quantities": q.get("physical_quantities") or [v.get("name") for v in q.get("variables", []) if v.get("name")],
            "task_archetypes": [
                {"task": t.get("task"), "confidence": t.get("confidence", 0.5), "evidence_terms": t.get("evidence_terms", []), "evidence_ids": t.get("evidence_ids", [])}
                for t in q.get("task_archetypes", [])
            ],
            "outputs_required": [
                {"artifact": o.get("type") or o.get("artifact"), "confidence": o.get("confidence", 0.5), "evidence_ids": o.get("evidence_ids", [])}
                for o in q.get("required_outputs", [])
            ],
            "constraints": [c.get("text", str(c)) if isinstance(c, dict) else str(c) for c in (q.get("constraints") or [])],
            "data_requirements": q.get("data_requirements", []),
            "negative_evidence": q.get("negative_evidence", []),
            "source_evidence_ids": q.get("source_evidence_ids", []),
            "understanding_mode": final_sig.get("mode", "unknown"),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "failed" if final_sig.get("status") == "failed" else "passed",
        "case_id": case_id,
        "timestamp": now_iso(),
        "mode": "compatibility_view_of_problem_understanding_engine",
        "questions": questions,
        "note": "Generated from workspace/problem_understanding/official/final_problem_signature.json. Prefer problem-understand + understanding-gate for v7.1 workflows.",
    }


def _entities_from_variables(vars_: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for v in vars_[:20]:
        if v.get("name"):
            out.append({"name": v.get("name"), "role": v.get("role", "variable"), "evidence_ids": v.get("evidence_ids", [])})
    return out


def _gate_decision(critic: dict[str, Any], validation: dict[str, Any], strict: bool) -> dict[str, Any]:
    blocking = []
    warnings = []
    for issue in validation.get("issues", []):
        (blocking if issue.get("severity") == "critical" else warnings).append(issue)
    for issue in critic.get("issues", []):
        if issue.get("severity") == "high":
            blocking.append(issue)
        else:
            warnings.append(issue)
    status = "failed" if blocking else ("warning" if warnings else "passed")
    if strict and status == "warning":
        next_action = "revise_or_agent_review_problem_signature"
    elif status == "failed":
        next_action = "revise_problem_signature_before_academic_search"
    else:
        next_action = "academic-search"
    return {
        "schema_version": SCHEMA_VERSION,
        "gate": "understanding_gate",
        "status": status,
        "blocking_issue_count": len(blocking),
        "warning_count": len(warnings),
        "blocking_issues": blocking,
        "warnings": warnings,
        "next_action": next_action,
        "policy": {
            "no_evidence_no_claim": True,
            "facts_inferences_recommendations_must_be_separated": True,
            "external_agent_review_recommended_for_competition_submission": True,
        },
    }


def _filter_question(sig: dict[str, Any], question_id: str) -> dict[str, Any]:
    out = dict(sig)
    questions = sig.get("questions") or {}
    out["questions"] = {question_id: questions.get(question_id, {})} if question_id in questions else {}
    return out
