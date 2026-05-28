from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from mmos.quality_oracle.common import question_ids

GENERIC_VERIFIER = r'''#!/usr/bin/env python3
from __future__ import annotations
import json, os
from pathlib import Path

def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except Exception:
        return default

def extract_metric(sol):
    if not isinstance(sol, dict):
        return None, None
    for key in ['objective_value','score','value','annual_output_mw','unit_area_output_kw_m2']:
        if isinstance(sol.get(key), (int, float)):
            return key, float(sol[key])
    metrics = sol.get('metrics') or {}
    if isinstance(metrics, dict):
        for key, val in metrics.items():
            if isinstance(val, (int, float)):
                return 'metrics.' + key, float(val)
    return None, None

def main():
    case_dir = Path(os.environ['MMOS_CASE_DIR'])
    qid = os.environ['MMOS_QUESTION_ID']
    abs_tol = float(os.environ.get('MMOS_ABS_TOL', '1e-6'))
    rel_tol = float(os.environ.get('MMOS_REL_TOL', '0.05'))
    real = read_json(case_dir/'results'/qid/'outputs'/'solution_real.json', {})
    reduced = read_json(case_dir/'results'/qid/'outputs'/'solution_reduced.json', {})
    metric, solver_value = extract_metric(real)
    rmetric, recomputed_value = extract_metric(reduced)
    if metric is None or recomputed_value is None:
        status = 'failed'
        failure = 'NO_RECOMPUTABLE_METRIC_PAIR'
        diff = rel = None
    else:
        diff = abs(solver_value - recomputed_value)
        rel = diff / max(abs(solver_value), abs(recomputed_value), 1.0)
        status = 'passed' if diff <= abs_tol or rel <= rel_tol else 'failed'
        failure = None if status == 'passed' else 'RECOMPUTE_MISMATCH'
    print(json.dumps({
        'status': status,
        'verifier': 'generic_reduced_vs_real_metric_recompute',
        'question_id': qid,
        'method': 'independent script comparing reduced and real artifacts without importing solve.py',
        'metric': metric,
        'solver_value': solver_value,
        'recomputed_value': recomputed_value,
        'abs_error': diff,
        'rel_error': rel,
        'abs_tol': abs_tol,
        'rel_tol': rel_tol,
        'failure': failure,
    }, ensure_ascii=False))

if __name__ == '__main__':
    main()
'''


def scaffold_verifier(case_dir: Path, question_id: str | None = None, force: bool = False) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    created=[]
    for qid in question_ids(case_dir, question_id):
        vdir = case_dir / 'engineering' / 'questions' / qid / 'verifiers'
        vdir.mkdir(parents=True, exist_ok=True)
        path = vdir / 'recompute_metric.py'
        if force or not path.exists():
            path.write_text(GENERIC_VERIFIER, encoding='utf-8')
            path.chmod(0o755)
        created.append(str(path.relative_to(case_dir)))
    return {'status': 'ok' if created else 'failed', 'created': created, 'code': None if created else 'NO_QUESTIONS'}


def run_verifiers(case_dir: Path, question_id: str | None = None, abs_tol: float = 1e-6, rel_tol: float = 0.05, timeout: int = 30) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    reports=[]; failures=[]; warnings=[]
    for qid in question_ids(case_dir, question_id):
        vdir = case_dir / 'engineering' / 'questions' / qid / 'verifiers'
        plugins = sorted(p for p in vdir.glob('*.py') if p.name != '__init__.py') if vdir.exists() else []
        if not plugins:
            failures.append({'question_id': qid, 'code': 'NO_VERIFIER_PLUGINS', 'path': str(vdir.relative_to(case_dir))})
            continue
        out_dir = case_dir / 'results' / qid / 'independent_verification' / 'plugins'
        out_dir.mkdir(parents=True, exist_ok=True)
        for plugin in plugins:
            env = dict(os.environ)
            env.update({'MMOS_CASE_DIR': str(case_dir), 'MMOS_QUESTION_ID': qid, 'MMOS_ABS_TOL': str(abs_tol), 'MMOS_REL_TOL': str(rel_tol)})
            proc = subprocess.run([sys.executable, str(plugin)], cwd=str(case_dir), env=env, text=True, capture_output=True, timeout=timeout)
            try:
                payload = json.loads((proc.stdout or '').strip().splitlines()[-1])
            except Exception:
                payload = {'status': 'failed', 'error': 'VERIFIER_DID_NOT_EMIT_JSON', 'stdout': proc.stdout[-1000:], 'stderr': proc.stderr[-1000:], 'returncode': proc.returncode}
            payload.setdefault('question_id', qid)
            payload['plugin'] = str(plugin.relative_to(case_dir))
            payload['returncode'] = proc.returncode
            if proc.returncode != 0:
                payload['status'] = 'failed'
                payload['stderr'] = proc.stderr[-2000:]
            write_json(out_dir / f'{plugin.stem}.json', payload)
            reports.append(payload)
            if payload.get('status') == 'failed':
                failures.append({'question_id': qid, 'code': 'VERIFIER_PLUGIN_FAILED', 'plugin': str(plugin.relative_to(case_dir)), 'report': payload})
            elif payload.get('status') == 'warning':
                warnings.append({'question_id': qid, 'code': 'VERIFIER_PLUGIN_WARNING', 'plugin': str(plugin.relative_to(case_dir)), 'report': payload})
    status = 'failed' if failures else ('warning' if warnings else 'passed')
    report = {'gate': 'verifier-run', 'status': status, 'reports': reports, 'failures': failures, 'warnings': warnings, 'generated_at': now_iso()}
    write_json(case_dir / 'quality' / 'verifier_run_report.json', report)
    return report


def compare_verifiers(case_dir: Path, question_id: str | None = None, strict: bool = False) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    compared=[]; failures=[]; warnings=[]
    for qid in question_ids(case_dir, question_id):
        out_dir = case_dir / 'results' / qid / 'independent_verification' / 'plugins'
        reports = [read_json(p, {}) or {} for p in sorted(out_dir.glob('*.json'))] if out_dir.exists() else []
        if not reports:
            item = {'question_id': qid, 'code': 'NO_VERIFIER_PLUGIN_REPORTS', 'path': str(out_dir.relative_to(case_dir))}
            (failures if strict else warnings).append(item)
            continue
        passed = [r for r in reports if r.get('status') == 'passed']
        failed = [r for r in reports if r.get('status') == 'failed']
        compared.append({'question_id': qid, 'plugin_count': len(reports), 'passed_count': len(passed), 'failed_count': len(failed), 'reports': reports})
        if failed:
            failures.append({'question_id': qid, 'code': 'SOME_VERIFIERS_FAILED', 'failed_count': len(failed)})
        if not passed:
            failures.append({'question_id': qid, 'code': 'NO_PASSING_VERIFIER'})
    status = 'failed' if failures else ('warning' if warnings else 'passed')
    report = {'gate': 'verifier-compare', 'status': status, 'strict': strict, 'compared': compared, 'failures': failures, 'warnings': warnings, 'generated_at': now_iso()}
    write_json(case_dir / 'quality' / 'verifier_compare_report.json', report)
    # Also mirror question-local reports for independent_verify and evidence pack.
    for item in compared:
        qid = item.get('question_id')
        write_json(case_dir / 'results' / qid / 'independent_verification' / 'verifier_compare.json', item)
    return report
