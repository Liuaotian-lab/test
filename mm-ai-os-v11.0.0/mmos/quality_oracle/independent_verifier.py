from __future__ import annotations
from pathlib import Path
from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from .common import ensure_quality_dirs, question_ids, read_solution, write_report


def _extract_metric(sol: dict):
    for k in ['objective_value','unit_area_output_kw_m2','annual_output_mw','score','value']:
        if isinstance(sol.get(k), (int,float)):
            return k, float(sol[k])
    metrics = sol.get('metrics') or {}
    if isinstance(metrics, dict):
        for k,v in metrics.items():
            if isinstance(v,(int,float)):
                return f'metrics.{k}', float(v)
    return None, None


def independent_verify(case_dir: Path, question_id: str | None = None, abs_tol: float = 1e-6, rel_tol: float = 0.05) -> dict:
    case_dir = Path(case_dir).resolve(); ensure_quality_dirs(case_dir)
    failures=[]; warnings=[]; verified=[]
    for qid in question_ids(case_dir, question_id):
        real = read_solution(case_dir, qid)
        reduced = read_json(case_dir/'results'/qid/'outputs'/'solution_reduced.json', {}) or {}
        if not real:
            failures.append({'question_id':qid,'code':'MISSING_REAL_RESULT'})
            continue
        metric, val = _extract_metric(real)
        rmetric, rval = _extract_metric(reduced)
        plugin_compare = read_json(case_dir/'results'/qid/'independent_verification'/'verifier_compare.json', {}) or {}
        if plugin_compare and plugin_compare.get('passed_count', 0) > 0 and plugin_compare.get('failed_count', 0) == 0:
            verified.append({'question_id':qid,'method':'verifier_plugin_compare','status':'passed','details':plugin_compare})
        elif metric and rmetric and isinstance(rval,(int,float)):
            diff = abs(val-rval); rel = diff / max(abs(val), abs(rval), 1.0)
            status = 'passed' if diff <= abs_tol or rel <= rel_tol else 'warning'
            if status == 'warning':
                warnings.append({'question_id':qid,'code':'REDUCED_REAL_METRIC_DIFF_LARGE','metric':metric,'real':val,'reduced':rval,'rel_diff':rel})
            verified.append({'question_id':qid,'method':'reduced_vs_real_consistency','metric':metric,'real_value':val,'independent_value':rval,'relative_diff':rel,'status':status})
        else:
            # Solver-declared verification is retained as weak evidence only; verifier plugins are preferred.
            diag = real.get('diagnostics',{}) or {}
            if diag.get('independent_verification'):
                warnings.append({'question_id':qid,'code':'ONLY_SOLVER_DECLARED_INDEPENDENT_VERIFICATION','message':'独立验证来自 solver 自声明，建议实现 engineering/questions/<QID>/verifiers 插件。'})
                verified.append({'question_id':qid,'method':'solver_declared_independent_verification_weak','status':'warning','details':diag.get('independent_verification')})
            else:
                warnings.append({'question_id':qid,'code':'NO_INDEPENDENT_VERIFICATION_AVAILABLE','message':'建议实现另一套公式/采样/solver 交叉验证。'})
                verified.append({'question_id':qid,'method':'none','status':'warning'})
        # Write question-local report for downstream evidence collection.
        write_json(case_dir/'results'/qid/'independent_verification'/'independent_verification.json', verified[-1])
    report={'gate':'independent-verify','status':'failed' if failures else ('warning' if warnings else 'passed'), 'verified':verified, 'failures':failures, 'warnings':warnings, 'generated_at':now_iso()}
    return write_report(case_dir, 'independent_verification_report.json', report)
