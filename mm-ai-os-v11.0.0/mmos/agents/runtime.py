from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from mmos.agents.budget import evaluate_budget
from mmos.agents.policy import ensure_policy, evaluate_path_permission
from mmos.kernel.events import now_iso
from mmos.kernel.jsonio import read_json, write_json


def run_report_path(case_dir: Path, run_id: str) -> Path:
    return Path(case_dir) / ".agent" / "run_reports" / f"{run_id}.json"


def create_agent_run_report(
    case_dir: Path,
    *,
    task_id: str,
    agent_role: str = "deterministic_agent",
    context_files: list[str] | None = None,
    candidate_outputs: list[str] | None = None,
    commands_run: list[str] | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
    status: str = "completed",
) -> dict[str, Any]:
    case_dir = Path(case_dir)
    ensure_policy(case_dir)
    context_files = context_files or []
    candidate_outputs = candidate_outputs or []
    commands_run = commands_run or []
    tool_calls = tool_calls or []
    permission_checks = [evaluate_path_permission(case_dir, p, operation="write") for p in candidate_outputs]
    usage = {
        "context_files": len(context_files),
        "candidate_outputs": len(candidate_outputs),
        "tool_calls": len(tool_calls) + len(commands_run),
        "search_queries": 0,
        "runtime_seconds": 0,
    }
    budget = evaluate_budget(usage)
    if not budget["allowed"] or any(not c["allowed"] for c in permission_checks):
        status = "blocked"
    run_id = f"run_{now_iso().replace(':','').replace('-','').replace('.','_')}_{uuid4().hex[:8]}"
    report = {
        "schema_version": "8.0.0",
        "run_id": run_id,
        "task_id": task_id,
        "agent_role": agent_role,
        "case_id": case_dir.name,
        "context_files": context_files,
        "allowed_files": ["workspace/**/candidate/**", "paper/candidate/**", ".agent/run_reports/**"],
        "modified_files": candidate_outputs,
        "candidate_outputs": candidate_outputs,
        "commands_run": commands_run,
        "tool_calls": tool_calls,
        "permission_checks": permission_checks,
        "budget_check": budget,
        "schema_checks": [],
        "gate_results": [],
        "status": status,
        "created_at": now_iso(),
    }
    p = run_report_path(case_dir, run_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    write_json(p, report)
    return report


def latest_agent_run_report(case_dir: Path) -> dict[str, Any]:
    root = Path(case_dir) / ".agent" / "run_reports"
    reports = sorted(root.glob("run_*.json")) if root.exists() else []
    if not reports:
        return {"status": "not_found", "case_id": Path(case_dir).name}
    return read_json(reports[-1], {})
