from __future__ import annotations
from pathlib import Path
from mmos.kernel.events import now_iso
from mmos.kernel.jsonio import read_json, write_json
from mmos.quality_oracle.common import ensure_quality_dirs, question_ids, read_solution, write_report, QUALITY_LEVEL_SCORE, MODEL_LEVEL_SCORE


def _metric(sol: dict):
    for k in ['objective_value','unit_area_output_kw_m2','annual_output_mw','score','value']:
        if isinstance(sol.get(k), (int,float)):
            return k, float(sol[k])
    metrics=sol.get('metrics') or {}
    if isinstance(metrics, dict):
        for k,v in metrics.items():
            if isinstance(v,(int,float)):
                return f'metrics.{k}', float(v)
    return 'objective_value', None


def _candidate_from_solution(qid: str, label: str, sol: dict) -> dict:
    metric, value = _metric(sol)
    diag = sol.get('diagnostics',{}) or {}
    model_level = diag.get('model_level') or ('L3' if sol.get('quality_level') in {'heuristic_feasible','simulation_estimate'} else 'L2')
    qscore = QUALITY_LEVEL_SCORE.get(sol.get('quality_level'), 0.2)
    mscore = MODEL_LEVEL_SCORE.get(model_level, 0.3)
    feasible = sol.get('status') in {'success','ok','passed'} and diag.get('constraints_checked', True) is not False
    combined = (0.45*qscore + 0.35*mscore + 0.20*(1.0 if feasible else 0.0))
    return {'question_id':qid,'solver':label,'metric':metric,'objective_value':value,'quality_level':sol.get('quality_level'),'model_level':model_level,'constraint_status':'passed' if feasible else 'failed','combined_score':round(combined,4),'risk':diag.get('risk') or diag.get('warnings') or []}


def solver_tournament(case_dir: Path, question_id: str | None = None, budget: str = 'regression', min_candidates: int = 3) -> dict:
    case_dir=Path(case_dir).resolve(); ensure_quality_dirs(case_dir)
    questions={}; warnings=[]; failures=[]
    for qid in question_ids(case_dir, question_id):
        candidates=[]
        real = read_solution(case_dir, qid)
        if real:
            candidates.append(_candidate_from_solution(qid, 'primary_real_solver', real))
        # Discover optional variant outputs.
        variant_dir = case_dir/'results'/qid/'tournament'
        for p in sorted(variant_dir.glob('*.json')) if variant_dir.exists() else []:
            if p.name == 'solution_tournament.json':
                continue
            sol = read_json(p, {}) or {}
            if sol:
                candidates.append(_candidate_from_solution(qid, p.stem, sol))
        if not candidates:
            failures.append({'question_id':qid,'code':'NO_TOURNAMENT_CANDIDATES'})
            questions[qid]={'status':'failed','candidates':[]}
            continue
        if len(candidates) < min_candidates:
            warnings.append({'question_id':qid,'code':'SOLVER_DIVERSITY_INSUFFICIENT','message':f'候选 solver 数量不足：{len(candidates)} < {min_candidates}；高置信结果至少需要 baseline + competition + verifier。', 'candidate_count': len(candidates), 'min_candidates': min_candidates})
        selected = sorted(candidates, key=lambda c: (c['constraint_status']=='passed', c['combined_score'], c['objective_value'] if isinstance(c.get('objective_value'),(int,float)) else -1), reverse=True)[0]
        result={'question_id':qid,'budget':budget,'status':'warning' if len(candidates)<min_candidates else 'passed','min_candidates':min_candidates,'candidates':candidates,'selected_solution':selected['solver'],'selection_reason':'按约束状态、质量等级、模型成熟度和目标值综合选择；非单纯选择最高目标值。','generated_at':now_iso()}
        write_json(case_dir/'results'/qid/'tournament'/'solution_tournament.json', result)
        questions[qid]=result
    report={'gate':'solver-tournament','status':'failed' if failures else ('warning' if warnings else 'passed'),'questions':questions,'failures':failures,'warnings':warnings,'generated_at':now_iso()}
    return write_report(case_dir, 'solver_tournament_report.json', report)
