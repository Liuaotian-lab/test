from __future__ import annotations
from pathlib import Path
from mmos.modeling_os.common import read_jsonl, append_jsonl, write_json, status_from


def experiment_pack(case_dir: Path) -> dict:
    case_dir = Path(case_dir).resolve()
    rows=[]
    for base in [case_dir/'engineering'/'results', case_dir/'results']:
        if base.exists():
            for path in sorted(base.rglob('experiments.jsonl')):
                rows.extend(read_jsonl(path))
    failures=[]; warnings=[]
    seen=set(); unique=[]
    for row in rows:
        key=(row.get('experiment_id'), row.get('question_id'))
        if key in seen:
            continue
        seen.add(key); unique.append(row)
        if not row.get('limitations'):
            failures.append({'code':'EXPERIMENT_LIMITATIONS_MISSING','experiment_id':row.get('experiment_id')})
    if not unique:
        failures.append({'code':'NO_EXPERIMENT_RECORDS','message':'No experiments.jsonl files were found.'})
    append_jsonl(case_dir/'reports'/'experiments_summary.jsonl', unique)
    report={'status':status_from(failures,warnings),'experiment_count':len(unique),'failures':failures,'warnings':warnings,'summary':'reports/experiments_summary.jsonl'}
    write_json(case_dir/'reports'/'experiments_pack_report.json', report)
    return report
