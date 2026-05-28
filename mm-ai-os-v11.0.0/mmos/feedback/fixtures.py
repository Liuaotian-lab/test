from __future__ import annotations
from pathlib import Path
import subprocess, sys, json, shutil
from mmos.kernel.jsonio import write_json


def run_fixtures(os_root: Path, budget: str = 'regression') -> dict:
    """Run built-in fixture suite.

    Keep this runner deterministic and avoid long-lived shell pipelines. Some
    acceptance scripts may invoke nested Python processes; for the canonical
    smoke fixture we call run_self_test directly so fixture-run remains stable
    in unattended CI and zip-check environments.
    """
    os_root=Path(os_root).resolve(); fixtures=os_root/'tests'/'fixtures'
    results=[]
    for fx in sorted(fixtures.glob('*')):
        if not fx.is_dir() or fx.name.startswith('_'):
            continue
        if fx.name == 'smoke_complete':
            try:
                from mmos.feedback.selftest import run_self_test
                case_id='fixture_smoke_complete'
                report=run_self_test(os_root, case_id=case_id, budget='fast' if budget=='fast' else budget)
                status='passed' if report.get('status')=='passed' and report.get('duration_sec', 9999) < 120 else 'failed'
                results.append({'fixture':fx.name,'status':status,'return_code':0 if status=='passed' else 1,'log':f"smoke_complete passed in {report.get('duration_sec')} sec"})
                shutil.rmtree(os_root/'cases'/case_id, ignore_errors=True)
            except Exception as exc:
                results.append({'fixture':fx.name,'status':'failed','return_code':1,'log':str(exc)})
            continue
        if fx.name == 'security_and_gate_regression':
            try:
                proc = subprocess.run(
                    [sys.executable, str(os_root / 'tests' / 'regression_gate_checks.py')],
                    cwd=str(os_root),
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=300,
                )
                log = proc.stdout or ''
                results.append({'fixture':fx.name,'status':'passed' if proc.returncode==0 else 'failed','return_code':proc.returncode,'log':log[-4000:]})
            except subprocess.TimeoutExpired as exc:
                results.append({'fixture':fx.name,'status':'failed','return_code':124,'log':f'fixture timed out: {exc}'})
            continue
        script=fx/'acceptance_commands.sh'
        if not script.exists():
            results.append({'fixture':fx.name,'status':'skipped','reason':'missing acceptance_commands.sh'})
            continue
        try:
            proc=subprocess.run(
                ['bash', str(script)],
                cwd=str(os_root),
                text=True,
                encoding='utf-8',
                errors='replace',
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=300,
            )
            log = proc.stdout or ''
            results.append({'fixture':fx.name,'status':'passed' if proc.returncode==0 else 'failed','return_code':proc.returncode,'log':log[-4000:]})
        except subprocess.TimeoutExpired as exc:
            results.append({'fixture':fx.name,'status':'failed','return_code':124,'log':f'fixture timed out: {exc}'})
    out={'status':'failed' if any(r['status']=='failed' for r in results) else 'passed','fixtures':results}
    write_json(os_root/'tests'/'fixture_run_report.json', out)
    return out
