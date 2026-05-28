from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from mmos.kernel_gates.common import required_questions, status_from


def case_text(case_dir: Path) -> str:
    case_dir = Path(case_dir)
    parts: list[str] = []
    for rel in [
        'workspace/problem_corpus.md',
        'workspace/problem_understanding/candidate/final_problem_signature.json',
        'workspace/problem_signatures/case.signatures.json',
        'registry/questions_registry.json',
        'workspace/constraints/candidate/constraint_ledger.json',
        'workspace/constraints/official/constraint_ledger.json',
    ]:
        p = case_dir / rel
        if p.exists():
            parts.append(p.read_text(encoding='utf-8', errors='ignore'))
    raw = case_dir / 'data' / 'raw'
    if raw.exists():
        for p in sorted(raw.rglob('*')):
            if p.is_file():
                parts.append(p.name)
                if p.suffix.lower() in {'.txt', '.md', '.csv', '.json'}:
                    parts.append(p.read_text(encoding='utf-8', errors='ignore')[:20000])
    return '\n'.join(parts)


def qids(case_dir: Path) -> list[str]:
    return required_questions(Path(case_dir)) or ['Q1']


def load_atoms(root: Path) -> dict[str, dict[str, Any]]:
    atoms: dict[str, dict[str, Any]] = {}
    for p in sorted((Path(root) / 'mmos' / 'protocol_templates' / 'atoms').glob('*.yaml')):
        try:
            obj = json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            continue
        if isinstance(obj, dict) and obj.get('atom_id'):
            atoms[str(obj['atom_id'])] = obj
    return atoms


def read_compiled(case_dir: Path) -> dict[str, Any]:
    return read_json(Path(case_dir) / 'workspace' / 'dynamic_protocols' / 'official' / 'compiled_protocol.json', {}) or {}


def read_protocol(case_dir: Path) -> dict[str, Any]:
    p = Path(case_dir) / 'workspace' / 'dynamic_protocols' / 'candidate' / 'domain_protocol.yaml'
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return {}


def write_report(case_dir: Path, rel: str, report: dict[str, Any]) -> dict[str, Any]:
    report.setdefault('generated_at', now_iso())
    write_json(Path(case_dir) / rel, report)
    return report


def unique(seq):
    out=[]; seen=set()
    for x in seq:
        if x not in seen:
            seen.add(x); out.append(x)
    return out
