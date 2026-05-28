from __future__ import annotations
from pathlib import Path
from mmos.kernel.jsonio import read_json, write_json


def build_backlog(case_dir: Path) -> dict:
    case_dir = Path(case_dir).resolve()
    items = []
    for p in sorted((case_dir / 'runs').glob('*/stage_results/*.json')) if (case_dir / 'runs').exists() else []:
        r = read_json(p, {})
        if r.get('status') == 'failed':
            items.append({'stage': r.get('stage'), 'question_id': r.get('question_id'), 'severity': 'P1', 'symptom': r.get('reason') or f"return_code={r.get('return_code')}", 'source': str(p.relative_to(case_dir))})
    out = {'case_id': case_dir.name, 'items': items}
    write_json(case_dir / 'reports' / 'os_backlog.json', out)
    return out
