from __future__ import annotations
from pathlib import Path
from mmos.kernel.events import now_iso
from .common import ensure_quality_dirs, question_ids, read_solution, write_report

EFFICIENCY_KEYS = [
    'annual_optical_efficiency','annual_cosine_efficiency','annual_shadow_blocking_efficiency','annual_truncation_efficiency',
    'optical_efficiency','cosine_efficiency','shadow_blocking_efficiency','truncation_efficiency'
]


def _walk_numbers(prefix: str, obj, out: list[tuple[str, float]]):
    if isinstance(obj, dict):
        for k,v in obj.items():
            _walk_numbers(f'{prefix}.{k}' if prefix else str(k), v, out)
    elif isinstance(obj, list):
        for i,v in enumerate(obj[:200]):
            _walk_numbers(f'{prefix}[{i}]', v, out)
    elif isinstance(obj, (int,float)) and not isinstance(obj, bool):
        out.append((prefix, float(obj)))


def bound_check(case_dir: Path, question_id: str | None = None) -> dict:
    case_dir = Path(case_dir).resolve(); ensure_quality_dirs(case_dir)
    failures=[]; warnings=[]; checks=[]
    for qid in question_ids(case_dir, question_id):
        sol = read_solution(case_dir, qid)
        if not sol:
            failures.append({'question_id':qid,'code':'MISSING_SOLUTION_REAL','path':f'results/{qid}/outputs/solution_real.json'})
            continue
        nums=[]; _walk_numbers('', sol, nums)
        for key, val in nums:
            lk=key.lower()
            if any(k in lk for k in EFFICIENCY_KEYS) or lk.endswith('.efficiency'):
                if not (0 <= val <= 1.000001):
                    failures.append({'question_id':qid,'code':'EFFICIENCY_OUT_OF_BOUNDS','metric':key,'value':val})
        # Generic objective sanity
        obj = sol.get('objective_value') or sol.get('unit_area_output_kw_m2') or sol.get('annual_output_mw')
        if isinstance(obj,(int,float)) and obj < 0:
            failures.append({'question_id':qid,'code':'NEGATIVE_OBJECTIVE','value':obj})
        ql = sol.get('quality_level')
        diag = sol.get('diagnostics',{}) or {}
        if ql in {'heuristic_feasible','evaluated_best','approximate'} and diag.get('constraints_checked') is not True:
            warnings.append({'question_id':qid,'code':'CONSTRAINTS_NOT_EXPLICITLY_CHECKED','message':'结果不是严格最优时，建议显式记录 constraints_checked=true 或约束验证报告。'})
        if ql == 'approximate' and diag.get('model_level') in {None,'L0','L1'}:
            warnings.append({'question_id':qid,'code':'APPROXIMATE_MODEL_WEAK','message':'近似模型成熟度偏低，建议增加边界或物理/统计验证。'})
        checks.append({'question_id':qid,'numeric_metrics_checked':len(nums),'quality_level':ql,'diagnostics_keys':sorted(list(diag.keys()))})
    report={'gate':'bound-check','status':'failed' if failures else ('warning' if warnings else 'passed'), 'checks':checks, 'failures':failures, 'warnings':warnings, 'generated_at':now_iso()}
    return write_report(case_dir, 'bound_check_report.json', report)
