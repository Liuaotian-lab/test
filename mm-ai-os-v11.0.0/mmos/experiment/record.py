from __future__ import annotations
from pathlib import Path
from mmos.modeling_os.common import read_json, write_json, append_jsonl, sha256_file, now_iso, rel_to_case, solution_files, status_from


def _record_from_solution(case_dir: Path, sol_path: Path) -> dict:
    data = read_json(sol_path, {}) or {}
    artifacts = data.get('artifacts') or []
    output_hashes = {}
    for rel in artifacts:
        p = case_dir / rel
        if p.exists() and p.is_file():
            output_hashes[rel] = sha256_file(p)
    qid = str(data.get('question_id') or sol_path.parents[1].name if len(sol_path.parents) > 1 else 'QX')
    return {
        'experiment_id': data.get('experiment_id') or f'{qid}_experiment_unset',
        'question_id': qid,
        'model': data.get('model') or 'unspecified_model',
        'method': data.get('method') or 'unspecified_method',
        'quality_level': data.get('quality_level') or 'failed',
        'solver_status': data.get('solver_status') or 'failed',
        'scope': data.get('scope') or 'exploratory',
        'data_source': data.get('data_source') or 'demo_data',
        'parameters': data.get('parameters') or {},
        'metrics': data.get('metrics') or {},
        'conclusion': data.get('conclusion') or f'{qid} produced solver result {rel_to_case(case_dir, sol_path)}.',
        'limitations': data.get('limitations') or '',
        'artifacts': artifacts,
        'validators': (data.get('diagnostics') or {}).get('domain_validators_run') or data.get('validators') or [],
        'violation_count': int(data.get('violation_count', 999999)),
        'created_at': now_iso(),
        'input_hashes': data.get('input_hashes') or {},
        'output_hashes': output_hashes,
        'source_solution': rel_to_case(case_dir, sol_path),
    }


def experiment_record(case_dir: Path, question_id: str) -> dict:
    case_dir = Path(case_dir).resolve()
    failures=[]; warnings=[]; records=[]
    for sol in solution_files(case_dir, question_id):
        rec = _record_from_solution(case_dir, sol)
        records.append(rec)
        if not rec.get('limitations'):
            failures.append({'code':'EXPERIMENT_LIMITATIONS_MISSING','experiment_id':rec.get('experiment_id')})
        if not rec.get('artifacts'):
            warnings.append({'code':'EXPERIMENT_ARTIFACTS_EMPTY','experiment_id':rec.get('experiment_id')})
    if not records:
        failures.append({'code':'NO_SOLUTION_FOR_EXPERIMENT_RECORD','question_id':question_id})
    for base in [case_dir/'engineering'/'results'/question_id, case_dir/'results'/question_id]:
        if base.exists() or base.parent.exists():
            append_jsonl(base/'experiments.jsonl', records)
    report = {'status': status_from(failures, warnings), 'question_id': question_id, 'records': records, 'failures': failures, 'warnings': warnings}
    write_json(case_dir/'reports'/f'experiment_record_{question_id}.json', report)
    return report



def experiment_record_all(case_dir: Path) -> dict:
    case_dir = Path(case_dir).resolve()
    registry = read_json(case_dir / 'registry' / 'questions_registry.json', {}) or {}
    questions = registry.get('questions') or []
    qids = [str(q.get('question_id') or q.get('id')) for q in questions if q.get('question_id') or q.get('id')]
    if not qids:
        result_dirs = case_dir / 'results'
        if result_dirs.exists():
            qids = [p.name for p in sorted(result_dirs.iterdir()) if p.is_dir()]
    reports = [experiment_record(case_dir, qid) for qid in qids]
    failures = []
    warnings = []
    for report in reports:
        failures.extend(report.get('failures') or [])
        warnings.extend(report.get('warnings') or [])
    summary = {'status': status_from(failures, warnings), 'question_count': len(qids), 'questions': qids, 'reports': reports, 'failures': failures, 'warnings': warnings}
    write_json(case_dir / 'reports' / 'experiment_record_all.json', summary)
    return summary
