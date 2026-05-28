from __future__ import annotations

from pathlib import Path

from mmos.agents.budget import evaluate_budget
from mmos.agents.policy import ensure_policy, evaluate_path_permission
from mmos.agents.runtime import create_agent_run_report
from mmos.adapters.mcp.permissions import evaluate_mcp_call
from mmos.contracts.manager import ensure_case_scaffold
from mmos.workflows.state_machine import transition_case_state, load_case_state


def test_agent_cannot_write_official(tmp_path: Path):
    case = tmp_path / "case"
    ensure_case_scaffold(case)
    ensure_policy(case)
    denied = evaluate_path_permission(case, "workspace/problem_understanding/official/final_problem_signature.json", operation="write")
    allowed = evaluate_path_permission(case, "workspace/problem_understanding/candidate/draft.json", operation="write")
    assert denied["allowed"] is False
    assert allowed["allowed"] is True


def test_budget_limits_block_excessive_context():
    result = evaluate_budget({"context_files": 99, "tool_calls": 1})
    assert result["allowed"] is False
    assert any(c["metric"] == "context_files" and not c["ok"] for c in result["checks"])


def test_mcp_denies_dangerous_tool_and_audits(tmp_path: Path):
    case = tmp_path / "case"
    ensure_case_scaffold(case)
    result = evaluate_mcp_call(case, tool="shell.run", target="rm -rf /", mode="write")
    assert result["allowed"] is False
    assert (case / ".agent" / "audit" / "tool_calls.jsonl").exists()


def test_agent_run_report_blocks_official_output(tmp_path: Path):
    case = tmp_path / "case"
    ensure_case_scaffold(case)
    report = create_agent_run_report(case, task_id="unsafe", candidate_outputs=["workspace/x/official/bad.json"])
    assert report["status"] == "blocked"
    assert (case / ".agent" / "run_reports" / f"{report['run_id']}.json").exists()


def test_workflow_state_transition(tmp_path: Path):
    case = tmp_path / "case"
    ensure_case_scaffold(case)
    result = transition_case_state(case, step="ingest")
    state = load_case_state(case)
    assert result["status"] == "INGESTED"
    assert state["status"] == "INGESTED"
    assert "ingest" in state["completed_steps"]
