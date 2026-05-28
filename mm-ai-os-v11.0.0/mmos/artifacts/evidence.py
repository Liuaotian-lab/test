from __future__ import annotations
from pathlib import Path
from mmos.kernel.hashing import sha256_file
from mmos.kernel.jsonio import write_json, read_json
from mmos.kernel.events import now_iso

EVIDENCE_EXTS = {'.json','.csv','.xlsx','.xls','.md','.txt','.png','.jpg','.jpeg','.pdf'}


def evidence_pack(case_dir: Path, question_id: str | None = None) -> dict:
    case_dir = Path(case_dir).resolve()
    roots = []
    if question_id:
        roots = [case_dir / 'results' / question_id, case_dir / 'reports']
    else:
        roots = [case_dir / 'results', case_dir / 'reports', case_dir / 'final_outputs']
    files=[]
    for root in roots:
        if not root.exists():
            continue
        for p in sorted(root.rglob('*')):
            if p.is_file() and p.suffix.lower() in EVIDENCE_EXTS:
                files.append({'path': str(p.relative_to(case_dir)), 'sha256': sha256_file(p), 'size_bytes': p.stat().st_size})
    manifest={'case_id': case_dir.name, 'question_id': question_id, 'created_at': now_iso(), 'files': files}
    out = case_dir / 'evidence' / 'evidence_pack_manifest.json' if not question_id else case_dir / 'evidence' / 'packs' / f'{question_id}_evidence_manifest.json'
    write_json(out, manifest)
    md_lines=[f"# Evidence Pack: {case_dir.name}", '', f"- question_id: `{question_id or 'ALL'}`", f"- files: {len(files)}", '', '| path | sha256 | size |', '|---|---|---:|']
    for f in files:
        md_lines.append(f"| {f['path']} | `{f['sha256'][:12]}...` | {f['size_bytes']} |")
    md = '\n'.join(md_lines)+'\n'
    md_path = case_dir / 'evidence' / 'evidence_map.md' if not question_id else case_dir / 'evidence' / 'maps' / f'{question_id}_evidence_map.md'
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md, encoding='utf-8')
    return {'status': 'ok', 'manifest': str(out.relative_to(case_dir)), 'file_count': len(files)}
