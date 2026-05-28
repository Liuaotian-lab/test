from __future__ import annotations
from pathlib import Path
import subprocess, sys, uuid, os, signal
from mmos.kernel.events import now_iso, EventLog
from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.hashing import hash_paths, sha256_file
from mmos.gates.solver_verify import verify_solver_result

DEFAULT_STAGES = ['validate', 'reduced', 'real', 'report']
TIMEOUT_BY_BUDGET = {'fast': 60, 'regression': 300, 'full': 3600}


def latest_run_dir(case_dir: Path) -> Path | None:
    runs = sorted([p for p in (case_dir / 'runs').glob('*') if p.is_dir()]) if (case_dir / 'runs').exists() else []
    return runs[-1] if runs else None


def create_run(case_dir: Path, budget: str = 'regression') -> Path:
    run_id = now_iso().replace(':','').replace('-','').replace('+','_') + '_' + uuid.uuid4().hex[:6]
    run_dir = case_dir / 'runs' / run_id
    (run_dir / 'stage_logs').mkdir(parents=True, exist_ok=True)
    (run_dir / 'stage_results').mkdir(parents=True, exist_ok=True)
    (run_dir / 'checkpoints').mkdir(parents=True, exist_ok=True)
    write_json(run_dir / 'run_manifest.json', {'run_id': run_id, 'case_id': case_dir.name, 'budget_mode': budget, 'status': 'running', 'started_at': now_iso(), 'stages': []})
    return run_dir


def stage_script(case_dir: Path, question_id: str) -> Path:
    candidates = [
        case_dir / 'engineering' / 'questions' / question_id / 'run.py',
        case_dir / 'engineering' / question_id.lower() / 'run.py',
        case_dir / 'engineering' / question_id / 'run.py',
    ]
    for c in candidates:
        if c.exists(): return c
    return candidates[0]


def stage_timeout(case_dir: Path, question_id: str, stage: str, budget: str) -> int:
    contract = read_json(case_dir / 'contracts' / 'questions' / question_id / 'solver_budget.json', default={}) or {}
    mode = (contract.get('budget_modes') or {}).get(budget) or {}
    return int(mode.get('timeout_sec') or TIMEOUT_BY_BUDGET.get(budget, 300))


def snapshot_inputs(case_dir: Path, question_id: str) -> list[Path]:
    # A stage checkpoint is only reusable if all solver-relevant inputs are unchanged.
    # Earlier releases only hashed contracts/engineering files; changing raw data could
    # therefore leave a stale passed checkpoint reusable under --resume.
    roots = [
        case_dir / 'contracts' / 'questions' / question_id,
        case_dir / 'engineering' / 'questions' / question_id,
        case_dir / 'engineering' / 'common',
        case_dir / 'data' / 'raw',
        case_dir / 'data' / 'normalized',
        case_dir / 'data' / 'manifest',
        case_dir / 'workspace' / 'problem_corpus.md',
        case_dir / 'workspace' / 'problem_corpus.json',
    ]
    paths=[]
    for root in roots:
        if root.is_file():
            paths.append(root)
        elif root.exists():
            paths.extend([p for p in root.rglob('*') if p.is_file()])
    return paths


def snapshot_outputs(case_dir: Path, question_id: str) -> list[Path]:
    roots = [case_dir / 'results' / question_id, case_dir / 'reports']
    paths=[]
    for root in roots:
        if root.exists():
            paths.extend([p for p in root.rglob('*') if p.is_file()])
    return paths


def is_stage_completed(run_dir: Path, question_id: str, stage: str, current_input_hash: str | None = None) -> bool:
    p = run_dir / 'checkpoints' / f'{question_id}.{stage}.checkpoint.json'
    data = read_json(p, default={}) or {}
    if data.get('status') != 'passed':
        return False
    if current_input_hash is not None and data.get('input_hash') != current_input_hash:
        return False
    return True


def run_stage(case_dir: Path, question_id: str, stage: str, run_dir: Path | None = None, budget: str = 'regression', resume: bool = False) -> dict:
    case_dir = Path(case_dir).resolve()
    run_dir = run_dir or create_run(case_dir, budget)
    input_files = snapshot_inputs(case_dir, question_id)
    input_hash = hash_paths(input_files)
    if resume and is_stage_completed(run_dir, question_id, stage, current_input_hash=input_hash):
        old = read_json(run_dir / 'checkpoints' / f'{question_id}.{stage}.checkpoint.json', {})
        old['skipped_by_resume'] = True
        old['resume_reason'] = 'checkpoint_input_hash_matches_current_inputs'
        return old
    elog = EventLog(run_dir / 'event_log.jsonl')
    script = stage_script(case_dir, question_id)
    started = now_iso()
    elog.emit('stage_started', question_id=question_id, stage=stage, script=str(script), input_hash=input_hash)
    stdout_path = run_dir / 'stage_logs' / f'{question_id}.{stage}.stdout.log'
    stderr_path = run_dir / 'stage_logs' / f'{question_id}.{stage}.stderr.log'
    timeout = stage_timeout(case_dir, question_id, stage, budget)
    if not script.exists():
        result = {'question_id': question_id, 'stage': stage, 'status': 'failed', 'reason': f'missing script {script}', 'started_at': started, 'finished_at': now_iso(), 'return_code': None, 'failure_code': 'MISSING_STAGE_SCRIPT', 'input_hash': input_hash}
    else:
        cmd = [sys.executable, str(script), stage, '--budget', budget]
        try:
            with stdout_path.open('w', encoding='utf-8') as out, stderr_path.open('w', encoding='utf-8') as err:
                proc = subprocess.run(cmd, cwd=str(case_dir), stdout=out, stderr=err, text=True, timeout=timeout)
            result = {'question_id': question_id, 'stage': stage, 'status': 'passed' if proc.returncode == 0 else 'failed', 'command': cmd, 'started_at': started, 'finished_at': now_iso(), 'return_code': proc.returncode, 'stdout_log': str(stdout_path.relative_to(case_dir)), 'stderr_log': str(stderr_path.relative_to(case_dir)), 'timeout_sec': timeout, 'input_hash': input_hash}
        except subprocess.TimeoutExpired as e:
            result = {'question_id': question_id, 'stage': stage, 'status': 'failed', 'command': cmd, 'started_at': started, 'finished_at': now_iso(), 'return_code': 124, 'failure_code': 'STAGE_TIMEOUT', 'timeout_sec': timeout, 'input_hash': input_hash, 'stdout_log': str(stdout_path.relative_to(case_dir)), 'stderr_log': str(stderr_path.relative_to(case_dir))}
    output_files = snapshot_outputs(case_dir, question_id)
    result['output_hash'] = hash_paths(output_files)
    result['outputs'] = [str(p.relative_to(case_dir)) for p in output_files]
    if stage == 'real' and result.get('status') == 'passed':
        solver_path = case_dir / 'results' / question_id / 'outputs' / 'solution_real.json'
        verification = verify_solver_result(solver_path) if solver_path.exists() else {'status': 'failed', 'failures': [{'code': 'MISSING_REAL_SOLUTION', 'path': str(solver_path.relative_to(case_dir))}]}
        write_json(run_dir / 'stage_results' / f'{question_id}.real.solver_verify.inline.json', verification)
        if verification.get('status') == 'failed':
            result['status'] = 'failed'
            result['failure_code'] = 'REAL_SOLVER_VERIFY_FAILED'
            result['solver_verify'] = verification
    write_json(run_dir / 'stage_results' / f'{question_id}.{stage}.result.json', result)
    write_json(run_dir / 'checkpoints' / f'{question_id}.{stage}.checkpoint.json', result)
    update_manifest(run_dir, result)
    update_agent_status(case_dir, question_id, stage, result.get('status'))
    elog.emit('stage_finished', **result)
    return result


def update_manifest(run_dir: Path, stage_result: dict) -> None:
    manifest_path = run_dir / 'run_manifest.json'
    manifest = read_json(manifest_path, {'stages': []}) or {'stages': []}
    manifest.setdefault('stages', []).append(stage_result)
    if stage_result.get('status') == 'failed':
        manifest['status'] = 'failed'
        manifest['failed_stage'] = f"{stage_result.get('question_id')}.{stage_result.get('stage')}"
    else:
        manifest['last_successful_stage'] = f"{stage_result.get('question_id')}.{stage_result.get('stage')}"
    write_json(manifest_path, manifest)


def update_agent_status(case_dir: Path, question_id: str, stage: str, status: str | None) -> None:
    p = case_dir / '.agent' / 'question_status' / 'case_status.json'
    data = read_json(p, {'case_id': case_dir.name, 'questions': {}}) or {'case_id': case_dir.name, 'questions': {}}
    q = data.setdefault('questions', {}).setdefault(question_id, {})
    q.setdefault('stages', {})[stage] = {'status': status, 'updated_at': now_iso()}
    q['status'] = 'failed' if status == 'failed' else q.get('status', 'running')
    data['last_updated_at'] = now_iso()
    write_json(p, data)


def run_question_flow(case_dir: Path, question_id: str, budget: str = 'regression', resume: bool = True, stages: list[str] | None = None) -> dict:
    case_dir = Path(case_dir).resolve(); stages = stages or DEFAULT_STAGES
    run_dir = latest_run_dir(case_dir) if resume else None
    if run_dir is None or read_json(run_dir / 'run_manifest.json', {}).get('status') == 'passed':
        run_dir = create_run(case_dir, budget)
    results = []
    final_status = 'passed'
    for stage in stages:
        r = run_stage(case_dir, question_id, stage, run_dir, budget, resume=resume)
        results.append(r)
        if r.get('status') == 'failed':
            final_status = 'failed'
            break
    finalize_run(run_dir, final_status)
    return {'run_dir': str(run_dir), 'results': results, 'status': final_status}


def run_case_flow(case_dir: Path, budget: str = 'regression', resume: bool = True) -> dict:
    case_dir = Path(case_dir).resolve()
    reg = read_json(case_dir / 'registry' / 'questions_registry.json', {'questions': []}) or {'questions': []}
    run_dir = latest_run_dir(case_dir) if resume else None
    if run_dir is None or read_json(run_dir / 'run_manifest.json', {}).get('status') == 'passed':
        run_dir = create_run(case_dir, budget)
    all_results = []
    required_questions = [q for q in reg.get('questions', []) if q.get('required', True) is not False]
    if not required_questions:
        finalize_run(run_dir, 'failed')
        return {'run_dir': str(run_dir), 'results': [], 'status': 'failed', 'failure_code': 'NO_REQUIRED_QUESTIONS'}
    for q in required_questions:
        qid = q.get('question_id') or q.get('id')
        for stage in DEFAULT_STAGES:
            r = run_stage(case_dir, qid, stage, run_dir, budget, resume=resume)
            all_results.append(r)
            if r.get('status') == 'failed':
                finalize_run(run_dir, 'failed')
                return {'run_dir': str(run_dir), 'results': all_results, 'status': 'failed'}
    finalize_run(run_dir, 'passed')
    return {'run_dir': str(run_dir), 'results': all_results, 'status': 'passed'}


def finalize_run(run_dir: Path, status: str):
    manifest = read_json(run_dir / 'run_manifest.json', {'stages': []}) or {'stages': []}
    if manifest.get('status') != 'failed':
        manifest['status'] = status
    manifest['finished_at'] = now_iso()
    write_json(run_dir / 'run_manifest.json', manifest)
