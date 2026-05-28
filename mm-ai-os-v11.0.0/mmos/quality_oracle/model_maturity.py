from __future__ import annotations
from pathlib import Path
from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from .common import ensure_quality_dirs, question_ids, read_solution, MODEL_LEVEL_SCORE, write_report

DEFAULT_MATURITY = {
    'L0': ['problem_restated'],
    'L1': ['baseline_model', 'basic_variables'],
    'L2': ['hard_constraints_checked', 'baseline_solver'],
    'L3': ['domain_specific_model', 'semantic_validation', 'sensitivity_plan'],
    'L4': ['multi_solver', 'independent_verification', 'red_team_review'],
    'L5': ['high_precision_validation', 'robustness_analysis', 'documented_improvement_loop']
}


def _method_plan_for_question(case_dir: Path, qid: str) -> dict:
    summary = read_json(case_dir / 'workspace' / 'method_plan' / 'case.method_plan_summary.json', {}) or {}
    plan = (summary.get('plans') or {}).get(qid)
    if plan:
        return plan
    return read_json(case_dir / 'workspace' / 'method_plan' / f'{qid}_method_plan.json', {}) or {}

def _declared_components(case_dir: Path, qid: str) -> set[str]:
    comps = set()
    for rel in [
        f'contracts/questions/{qid}/model_candidates.json',
        f'contracts/questions/{qid}/quality_contract.json',
        f'contracts/questions/{qid}/validation_contract.json',
        f'contracts/questions/{qid}/tool_contract.json',
    ]:
        data = read_json(case_dir/rel, {}) or {}
        text = str(data).lower()
        for token in ['baseline','constraint','semantic','sensitivity','multi_solver','independent','red_team','robustness','high_precision','domain']:
            if token in text:
                comps.add(token)
    sol = read_solution(case_dir, qid)
    diag = sol.get('diagnostics', {}) or {}
    if sol: comps.add('baseline_solver')
    if diag.get('constraints_checked') or diag.get('feasible') is True: comps.add('hard_constraints_checked')
    if diag.get('model_level'): comps.add(str(diag.get('model_level')))
    if diag.get('independent_verification'): comps.add('independent')
    if diag.get('sensitivity_analysis'): comps.add('sensitivity')
    if diag.get('multi_solver') or diag.get('solver_variants'): comps.add('multi_solver')
    return comps


def _infer_level(comps: set[str], solution: dict) -> str:
    diag = solution.get('diagnostics', {}) or {}
    if diag.get('model_level') in MODEL_LEVEL_SCORE:
        return diag.get('model_level')
    q = solution.get('quality_level')
    if q in {'global_optimal','certified_optimal'}:
        return 'L5'
    if q in {'exhaustive_best','evaluated_best'}:
        return 'L4'
    if q in {'heuristic_feasible','simulation_estimate'}:
        return 'L3'
    if q == 'approximate':
        return 'L2'
    if solution:
        return 'L1'
    return 'L0'


def method_candidates(case_dir: Path, question_id: str | None = None) -> dict:
    case_dir = Path(case_dir).resolve(); ensure_quality_dirs(case_dir)
    results = {}
    for qid in question_ids(case_dir, question_id):
        qtype = None
        reg = read_json(case_dir/'registry'/'questions_registry.json', {'questions': []}) or {'questions': []}
        for q in reg.get('questions', []):
            if (q.get('question_id') or q.get('id')) == qid:
                qtype = q.get('type')
        candidates = [
            {'id': 'baseline_feasible_model', 'level': 'L1', 'purpose': '快速形成可运行可行解'},
            {'id': f'{qtype or "generic"}_competition_model', 'level': 'L3', 'purpose': '达到该题型最低竞赛级模型成熟度'},
            {'id': 'alternative_solver_or_parameterization', 'level': 'L3', 'purpose': '提供独立模型/求解器对照'},
            {'id': 'local_refinement_and_robustness', 'level': 'L4', 'purpose': '改进目标值并检查鲁棒性'}
        ]
        if qtype and 'solar' in qtype:
            candidates.extend([
                {'id':'projection_shadow_blocking', 'level':'L3', 'purpose':'替代过弱遮挡模型'},
                {'id':'monte_carlo_truncation', 'level':'L3', 'purpose':'验证截断效率'},
                {'id':'concentric_ring_search', 'level':'L4', 'purpose':'高质量镜场布局族'},
                {'id':'ring_parameterized_variable_design', 'level':'L4', 'purpose':'Q3 分圈尺寸/高度优化'}
            ])
        payload = {'question_id': qid, 'generated_at': now_iso(), 'candidate_models': candidates, 'required_to_run': [c['id'] for c in candidates[:2]], 'recommended_to_run': [c['id'] for c in candidates[2:]]}
        out = case_dir/'contracts'/'questions'/qid/'model_candidates.json'
        write_json(out, payload)
        results[qid] = payload
    return write_report(case_dir, 'model_candidates_report.json', {'status':'ok', 'questions': results, 'generated_at': now_iso()})


def model_maturity_check(case_dir: Path, question_id: str | None = None) -> dict:
    case_dir = Path(case_dir).resolve(); ensure_quality_dirs(case_dir)
    items=[]; failures=[]; warnings=[]
    for qid in question_ids(case_dir, question_id):
        sol = read_solution(case_dir, qid)
        comps = _declared_components(case_dir, qid)
        level = _infer_level(comps, sol)
        score = MODEL_LEVEL_SCORE.get(level, 0.0)
        min_level = 'L3'
        plan = _method_plan_for_question(case_dir, qid)
        if plan.get('method_count', 0) >= 3 and plan.get('citation_count', 0) >= 1:
            min_level = 'L4' if plan.get('verification_approach') else 'L3'
        if MODEL_LEVEL_SCORE.get(level, 0) < MODEL_LEVEL_SCORE.get(min_level, 0):
            failures.append({'question_id': qid, 'code':'MODEL_MATURITY_BELOW_COMPETITION_LEVEL', 'level': level, 'minimum': min_level})
        if level in {'L0','L1','L2'}:
            warnings.append({'question_id': qid, 'code':'LOW_MODEL_MATURITY', 'message':'当前模型成熟度较低，建议执行 solution-improve，补充 method plan，或增加独立验证。'})
        items.append({'question_id': qid, 'model_level': level, 'score': round(score,3), 'minimum_competition_level': min_level, 'components_detected': sorted(comps)})
    report={'gate':'model-maturity-check','status':'failed' if failures else ('warning' if warnings else 'passed'), 'questions':items, 'failures':failures, 'warnings':warnings, 'generated_at':now_iso()}
    write_report(case_dir, 'model_maturity_report.json', report)
    write_json(case_dir/'workspace'/'model_maturity_report.json', report)
    return report
