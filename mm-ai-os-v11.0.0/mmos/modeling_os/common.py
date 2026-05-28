from __future__ import annotations
from pathlib import Path
import json, hashlib, datetime as _dt
from typing import Iterable, Any


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except Exception:
        return default


def write_json(path: Path, data: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding='utf-8')


def append_jsonl(path: Path, rows: Iterable[dict], overwrite: bool = True) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = 'w' if overwrite else 'a'
    with path.open(mode, encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')


def read_jsonl(path: Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    rows=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def status_from(failures: list, warnings: list | None = None) -> str:
    return 'failed' if failures else ('warning' if warnings else 'passed')


def rel_to_case(case_dir: Path, path: Path | str) -> str:
    p=Path(path)
    if not p.is_absolute():
        return p.as_posix().lstrip('./')
    try:
        return p.relative_to(case_dir).as_posix()
    except ValueError:
        return p.as_posix()


def resolve_case_file(case_dir: Path, rel: str | Path) -> Path:
    p=Path(rel)
    return p if p.is_absolute() else (case_dir / p)


def solution_files(case_dir: Path, question_id: str | None = None) -> list[Path]:
    roots = [case_dir / 'engineering' / 'results', case_dir / 'results']
    found=[]
    patterns = ['solution_*_real.json', 'solution_real.json']
    for root in roots:
        if not root.exists():
            continue
        search_root = root / question_id if question_id else root
        for pat in patterns:
            found.extend(sorted(search_root.rglob(pat)))
    # stable de-dup
    out=[]; seen=set()
    for p in found:
        rp=p.resolve()
        if rp not in seen:
            seen.add(rp); out.append(p)
    return out


def question_ids(case_dir: Path) -> list[str]:
    reg = read_json(case_dir / 'registry' / 'questions_registry.json', {}) or {}
    ids=[]
    for q in reg.get('questions', []) if isinstance(reg, dict) else []:
        qid=q.get('question_id') or q.get('id')
        if qid and q.get('required', True) is not False:
            ids.append(str(qid))
    if ids:
        return ids
    for base in [case_dir/'engineering'/'questions', case_dir/'questions', case_dir/'results', case_dir/'engineering'/'results']:
        if base.exists():
            ids.extend([p.name for p in base.iterdir() if p.is_dir() and p.name.upper().startswith('Q')])
    return sorted(set(ids))
