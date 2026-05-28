from __future__ import annotations

from pathlib import Path
from fnmatch import fnmatch
from typing import Any

from mmos.kernel.jsonio import read_json, write_json

DEFAULT_POLICY = {
    "schema_version": "8.0.0",
    "default_policy": "deny",
    "allow_read": ["context_packs/**", "docs/**", "mmos/**", "schemas/**", "tests/fixtures/**", "workspace/**/official/**"],
    "allow_write": ["workspace/**/candidate/**", "paper/candidate/**", ".agent/run_reports/**", ".agent/task_cards/**"],
    "deny_read": [".env", ".env.*", "secrets/**", "*.key", "*.pem"],
    "deny_write": ["workspace/**/official/**", "paper/official/**", "final_outputs/**", "package/**", "contracts/**", "schemas/**", "VERSION.txt", "VERSION_CODENAME", "os_manifest.json", ".env", ".env.*", "secrets/**", "*.key", "*.pem"],
    "approval_required": ["workspace/**/official/**", "paper/official/**", "final_outputs/**", "package/**", "schemas/**", "contracts/**", "state/**"],
}


def policy_path(case_dir: Path) -> Path:
    return Path(case_dir) / ".agent" / "allowed_files" / "agent_write_policy.json"


def ensure_policy(case_dir: Path) -> dict[str, Any]:
    p = policy_path(case_dir)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        write_json(p, DEFAULT_POLICY)
    return read_json(p, DEFAULT_POLICY) or DEFAULT_POLICY


def _rel(case_dir: Path, path: str | Path) -> str:
    path = Path(path)
    if path.is_absolute():
        try:
            path = path.relative_to(Path(case_dir).resolve())
        except ValueError:
            return str(path)
    return path.as_posix().lstrip("./")


def _match_any(patterns: list[str], value: str) -> bool:
    return any(fnmatch(value, pat) for pat in patterns)


def evaluate_path_permission(case_dir: Path, path: str | Path, *, operation: str = "write") -> dict[str, Any]:
    policy = ensure_policy(case_dir)
    rel = _rel(case_dir, path)
    deny_key = f"deny_{operation}"
    allow_key = f"allow_{operation}"
    denied = _match_any(policy.get(deny_key, []), rel)
    allowed = _match_any(policy.get(allow_key, []), rel)
    requires_approval = _match_any(policy.get("approval_required", []), rel)
    decision = "denied" if denied else ("allowed" if allowed else policy.get("default_policy", "deny"))
    if decision != "allowed":
        allowed_bool = False
    else:
        allowed_bool = True
    return {
        "schema_version": "8.0.0",
        "path": rel,
        "operation": operation,
        "allowed": allowed_bool,
        "decision": decision,
        "requires_approval": requires_approval,
        "policy_path": str(policy_path(case_dir).relative_to(case_dir)),
    }
