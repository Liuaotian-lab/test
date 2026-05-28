from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from mmos.kernel.events import now_iso
from mmos.kernel.jsonio import read_json, write_json

SCHEMA_VERSION = "8.0.0"

ORDER = [
    "CREATED", "INGESTED", "PARSED", "UNDERSTOOD", "RESEARCH_PLANNED",
    "RESEARCH_VERIFIED", "METHOD_PLANNED", "QUESTIONS_ACTIVATED", "SOLVED",
    "VERIFIED", "PAPER_BUILT", "FINAL_GATED", "PACKAGED",
]

STEP_TO_STATE = {
    "case_init": "CREATED",
    "ingest": "INGESTED",
    "parse": "PARSED",
    "understand": "UNDERSTOOD",
    "research_plan": "RESEARCH_PLANNED",
    "research_verify": "RESEARCH_VERIFIED",
    "method_plan": "METHOD_PLANNED",
    "question_activate": "QUESTIONS_ACTIVATED",
    "solve": "SOLVED",
    "verify": "VERIFIED",
    "paper_build": "PAPER_BUILT",
    "final_gate": "FINAL_GATED",
    "package": "PACKAGED",
}

@dataclass
class TransitionResult:
    schema_version: str
    case_id: str
    previous_status: str
    status: str
    step: str
    changed: bool
    state_path: str
    timestamp: str


def state_path(case_dir: Path) -> Path:
    return Path(case_dir) / "state" / "case_state.json"


def initial_state(case_dir: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": Path(case_dir).name,
        "status": "CREATED",
        "completed_steps": [],
        "artifacts": {},
        "last_gate": None,
        "updated_at": now_iso(),
    }


def load_case_state(case_dir: Path) -> dict[str, Any]:
    p = state_path(case_dir)
    if not p.exists():
        return initial_state(case_dir)
    data = read_json(p, {}) or {}
    data.setdefault("schema_version", SCHEMA_VERSION)
    data.setdefault("case_id", Path(case_dir).name)
    data.setdefault("status", "CREATED")
    data.setdefault("completed_steps", [])
    data.setdefault("artifacts", {})
    data.setdefault("last_gate", None)
    return data


def save_case_state(case_dir: Path, state: dict[str, Any]) -> dict[str, Any]:
    state = dict(state)
    state["schema_version"] = SCHEMA_VERSION
    state["case_id"] = Path(case_dir).name
    state["updated_at"] = now_iso()
    p = state_path(case_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    write_json(p, state)
    return state


def transition_case_state(
    case_dir: Path,
    *,
    step: str,
    status: str | None = None,
    artifact: dict[str, str] | None = None,
    gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    case_dir = Path(case_dir)
    state = load_case_state(case_dir)
    previous = state.get("status", "CREATED")
    target = status or STEP_TO_STATE.get(step)
    if target not in ORDER:
        raise ValueError(f"unknown workflow status: {target}")
    if previous not in ORDER:
        previous = "CREATED"
    changed = ORDER.index(target) >= ORDER.index(previous) and target != previous
    if ORDER.index(target) >= ORDER.index(previous):
        state["status"] = target
    steps = list(state.get("completed_steps", []))
    if step and step not in steps:
        steps.append(step)
    state["completed_steps"] = steps
    if artifact:
        artifacts = dict(state.get("artifacts", {}))
        artifacts.update(artifact)
        state["artifacts"] = artifacts
    if gate is not None:
        state["last_gate"] = gate
    save_case_state(case_dir, state)
    result = TransitionResult(
        schema_version=SCHEMA_VERSION,
        case_id=case_dir.name,
        previous_status=previous,
        status=state["status"],
        step=step,
        changed=changed,
        state_path=str(state_path(case_dir).relative_to(case_dir)),
        timestamp=now_iso(),
    )
    return asdict(result)


def case_state_report(case_dir: Path) -> dict[str, Any]:
    return load_case_state(Path(case_dir))
