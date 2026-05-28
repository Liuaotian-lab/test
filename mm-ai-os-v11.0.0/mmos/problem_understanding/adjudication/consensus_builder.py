from __future__ import annotations
from typing import Any


def choose_final_signature(candidate_bundle: dict[str, Any]) -> dict[str, Any]:
    """Choose final candidate.

    Agent-supplied candidate wins if present; otherwise the deterministic fallback is used.
    A future implementation can compare multiple Agent candidates and use a judge model.
    """
    candidates = candidate_bundle.get("candidates") or []
    for c in candidates:
        if c.get("candidate_id") == "agent_supplied" and c.get("signature"):
            sig = dict(c["signature"])
            sig["selected_candidate_id"] = "agent_supplied"
            sig["adjudication_mode"] = "agent_supplied_with_deterministic_validation"
            return sig
    if candidates:
        sig = dict(candidates[0].get("signature") or {})
        sig["selected_candidate_id"] = candidates[0].get("candidate_id")
        sig["adjudication_mode"] = "deterministic_fallback_until_agent_review"
        return sig
    return {"questions": {}, "selected_candidate_id": None, "adjudication_mode": "no_candidate"}
