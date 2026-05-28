from __future__ import annotations
from pathlib import Path
from mmos.kernel.events import now_iso
from mmos.kernel.jsonio import read_json, write_json
from mmos.quality_oracle.common import ensure_quality_dirs, question_ids, read_solution, write_report, MODEL_LEVEL_SCORE


def red_team_review(case_dir: Path, question_id: str | None = None) -> dict:
    case_dir=Path(case_dir).resolve(); ensure_quality_dirs(case_dir)
    findings=[]; questions=[]
    maturity = read_json(case_dir/'quality'/'model_maturity_report.json', {}) or {}
    maturity_by_q = {x.get('question_id'): x for x in maturity.get('questions', [])}
    outval = read_json(case_dir/'final_outputs'/'output_validation_report.json', {}) or {}
    for qid in question_ids(case_dir, question_id):
        sol = read_solution(case_dir, qid)
        qfind=[]
        if not sol:
            qfind.append({'severity':'P0','code':'MISSING_SOLUTION','message':'缺少 solution_real.json。'})
        else:
            ql = sol.get('quality_level')
            diag = sol.get('diagnostics',{}) or {}
            if ql in {'global_optimal','certified_optimal'} and not (diag.get('global_optimality_certificate') or diag.get('certificate_or_bound') or diag.get('duality_gap') is not None):
                qfind.append({'severity':'P0','code':'OVERCLAIMED_OPTIMALITY','message':'强最优性声明缺少证书或界。'})
            if ql in {'heuristic_feasible','evaluated_best'} and not diag.get('solver_variants') and not diag.get('multi_solver'):
                qfind.append({'severity':'P1','code':'HEURISTIC_WITHOUT_SOLVER_DIVERSITY','message':'启发式结果缺少多 solver 或多初值对比。'})
            if ql == 'approximate' and not diag.get('approximation_limitations'):
                qfind.append({'severity':'P1','code':'APPROXIMATION_LIMITS_NOT_DISCLOSED','message':'近似模型未披露限制。'})
        ml = maturity_by_q.get(qid, {})
        if ml and MODEL_LEVEL_SCORE.get(ml.get('model_level'),0) < MODEL_LEVEL_SCORE.get(ml.get('minimum_competition_level','L3'),0):
            qfind.append({'severity':'P1','code':'MODEL_BELOW_COMPETITION_LEVEL','message':f"模型成熟度 {ml.get('model_level')} 低于最低竞赛级 {ml.get('minimum_competition_level')}。"})
        qreport={'question_id':qid,'findings':qfind,'status':'failed' if any(f['severity']=='P0' for f in qfind) else ('warning' if qfind else 'passed')}
        write_json(case_dir/'.agent'/'red_team_reports'/f'{qid}_red_team_review.json', qreport)
        findings.extend([dict(f, question_id=qid) for f in qfind])
        questions.append(qreport)
    if outval.get('status') == 'failed':
        findings.append({'severity':'P0','code':'OUTPUT_VALIDATION_FAILED','message':'最终输出验证失败，不能 final。'})
    report={'gate':'red-team-review','status':'failed' if any(f['severity']=='P0' for f in findings) else ('warning' if findings else 'passed'),'questions':questions,'findings':findings,'generated_at':now_iso()}
    return write_report(case_dir, 'red_team_review.json', report)
