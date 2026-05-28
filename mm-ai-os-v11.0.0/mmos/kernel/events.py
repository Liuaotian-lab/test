from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
from .jsonio import append_jsonl


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


class EventLog:
    def __init__(self, path: Path):
        self.path = Path(path)

    def emit(self, event_type: str, **payload):
        append_jsonl(self.path, {'ts': now_iso(), 'event_type': event_type, **payload})
