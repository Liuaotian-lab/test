from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json
import re

from mmos.kernel.jsonio import read_json, write_json


def prompt_profile_list(root: Path) -> dict:
    d = Path(root) / ".agent" / "prompt_profiles"
    profiles = sorted(p.name for p in d.glob("*.md")) if d.exists() else []
    return {"status": "passed", "profiles": profiles}


def prompt_profile_show(root: Path, profile: str) -> dict:
    p = Path(root) / ".agent" / "prompt_profiles" / profile
    if not p.suffix:
        p = p.with_suffix(".md")
    if not p.exists():
        return {"status": "failed", "failures": [{"code": "MISSING_PROMPT_PROFILE", "profile": profile}]}
    return {"status": "passed", "profile": p.name, "content": p.read_text(encoding="utf-8")}


def task_card_build(case_dir: Path, *, role: str, question_id: str | None = None, profile: str = "modeling_agent_strict_v10", phase: str = "full_case") -> dict:
    case_dir = Path(case_dir)
    q = question_id or "ALL"
    card = {
        "case_id": case_dir.name,
        "role": role,
        "question_id": q,
        "phase": phase,
        "prompt_profile": profile,
        "allowed_read_paths": ["AGENTS.md", "context_packs/**", f"cases/{case_dir.name}/workspace/**", f"cases/{case_dir.name}/contracts/**", f"cases/{case_dir.name}/data/manifest/**"],
        "allowed_write_paths": [f"cases/{case_dir.name}/workspace/**/candidate/**", f"cases/{case_dir.name}/engineering/questions/{q}/**", f"cases/{case_dir.name}/results/{q}/**", f"cases/{case_dir.name}/quality/**", f"cases/{case_dir.name}/.agent/**"],
        "forbidden_paths": ["workspace/**/official/**", "final_outputs/**", "package/**", "schemas/**", "contracts/**", ".env", "secrets/**"],
        "required_commands": ["python -m compileall -q mmos scripts", f"python scripts/mmtool.py final-gate-v2 {case_dir.name} --strict"],
        "acceptance_gates": ["solver-verify", "constraint-coverage-check", "certificate-check", "semantic-redteam", "final-gate-v2"],
        "failure_policy": {"max_repair_attempts": 1, "must_write_failure_report": True},
    }
    out = case_dir / ".agent" / "task_cards" / f"{role}_{q}_{phase}.json"
    write_json(out, card)
    return {"status": "passed", "path": str(out), "task_card": card}


def failure_ledger_add(case_dir: Path, *, command: str = "unknown", return_code: int = 1, stdout_excerpt: str = "", stderr_excerpt: str = "", root_cause: str = "unknown") -> dict:
    case_dir = Path(case_dir)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", command)[:80]
    out = case_dir / ".agent" / "failures" / f"{ts}_{safe}.json"
    report = {"failed_command": command, "return_code": return_code, "stdout_excerpt": stdout_excerpt, "stderr_excerpt": stderr_excerpt, "root_cause": root_cause, "affected_questions": [], "affected_artifacts": [], "repair_action": None, "retry_count": 0, "final_status": "open"}
    write_json(out, report)
    return {"status": "passed", "path": str(out), "failure": report}


def repair_check(case_dir: Path) -> dict:
    case_dir = Path(case_dir)
    failures = []
    for p in (case_dir / ".agent" / "failures").glob("*.json"):
        obj = read_json(p, {}) or {}
        if int(obj.get("retry_count", 0) or 0) > 1:
            failures.append({"code": "REPAIR_RETRY_LIMIT_EXCEEDED", "path": str(p)})
    return {"status": "failed" if failures else "passed", "failures": failures, "warnings": []}
