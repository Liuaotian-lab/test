from __future__ import annotations

from pathlib import Path

from mmos.agents.budget import evaluate_budget
from mmos.adapters.mcp.permissions import evaluate_mcp_call
from mmos.contracts.manager import ensure_case_scaffold


def test_agent_runtime_core_commands_equivalent(tmp_path: Path):
    case = tmp_path / "runtime_cli_case"
    ensure_case_scaffold(case)
    assert evaluate_budget({"context_files": 99})["allowed"] is False
    assert evaluate_mcp_call(case, tool="shell.run", target="rm -rf /")["allowed"] is False
