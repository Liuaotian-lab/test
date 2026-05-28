from __future__ import annotations

from pathlib import Path
from typing import Any

from mmos.agents.audit import append_audit_event
from mmos.agents.policy import evaluate_path_permission

SAFE_TOOLS = {"filesystem.read", "search.query", "latex.compile.dry_run"}
WRITE_TOOLS = {"filesystem.write_candidate"}
DANGEROUS_TOOLS = {"filesystem.write", "shell.run", "database.write", "network.remote_mcp"}


def evaluate_mcp_call(case_dir: Path, *, tool: str, target: str | None = None, mode: str = "read") -> dict[str, Any]:
    if tool in DANGEROUS_TOOLS:
        allowed = False
        reason = "dangerous tool requires explicit human approval"
    elif tool in SAFE_TOOLS:
        allowed = True
        reason = "safe read-only or dry-run tool"
    elif tool in WRITE_TOOLS:
        perm = evaluate_path_permission(case_dir, target or "", operation="write")
        allowed = bool(perm["allowed"] and not perm["requires_approval"])
        reason = "candidate write permitted" if allowed else "write target denied or requires approval"
    else:
        allowed = False
        reason = "unknown MCP tool"
    result = {"schema_version": "8.0.0", "tool": tool, "target": target, "mode": mode, "allowed": allowed, "reason": reason}
    append_audit_event(case_dir, {"event_type": "mcp_permission_check", "tool": tool, "target": target, "allowed": allowed, "reason": reason})
    return result
