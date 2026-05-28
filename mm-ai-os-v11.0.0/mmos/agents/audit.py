from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from mmos.kernel.events import now_iso
from mmos.kernel.jsonio import read_json, write_json


def audit_log_path(case_dir: Path) -> Path:
    return Path(case_dir) / ".agent" / "audit" / "tool_calls.jsonl"


def append_audit_event(case_dir: Path, event: dict[str, Any]) -> dict[str, Any]:
    event = dict(event)
    event.setdefault("schema_version", "8.0.0")
    event.setdefault("event_id", f"evt_{uuid4().hex[:12]}")
    event.setdefault("timestamp", now_iso())
    p = audit_log_path(case_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    import json
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=True) + "\n")
    return {"status": "passed", "event": event, "audit_log": str(p.relative_to(case_dir))}
