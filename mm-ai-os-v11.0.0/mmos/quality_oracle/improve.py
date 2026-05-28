from __future__ import annotations
from pathlib import Path
from mmos.kernel.events import now_iso
from mmos.kernel.jsonio import read_json, write_json
from .common import ensure_quality_dirs, write_report


def _blocking_findings(red: dict) -> list[dict]:
    return [f for f in red.get('findings', []) if f.get('severity') in {'P0', 'P1'}]


def solution_improve(case_dir: Path, question_id: str | None = None, rounds: int = 3, budget: str = 'regression') -> dict:
    case_dir=Path(case_dir).resolve(); ensure_quality_dirs(case_dir)
    actions=[]
    maturity = read_json(case_dir/'quality'/'model_maturity_report.json', {}) or {}
    red = read_json(case_dir/'quality'/'red_team_review.json', {}) or {}
    bound = read_json(case_dir/'quality'/'bound_check_report.json', {}) or {}
    blockers = _blocking_findings(red)
    if not blockers and maturity.get('status') in {'passed','ok'} and bound.get('status') in {'passed','ok'}:
        actions.append({'round':1,'budget':budget,'source':'quality_gates','recommended_action':'no_blocking_improvement_required','accepted':True,'reason':'model_maturity, bound_check and red_team gates are already passed.'})
    else:
        for i in range(1, rounds+1):
            action='increase_solver_diversity_and_validation'
            source='default'
            for finding in blockers:
                action=f"fix_red_team_finding:{finding.get('code')}"; source='red_team'; break
            if action == 'increase_solver_diversity_and_validation' and maturity.get('status') in {'failed','warning'}:
                action='raise_model_maturity_to_minimum_competition_level'; source='model_maturity'
            if action == 'increase_solver_diversity_and_validation' and bound.get('status') in {'failed','warning'}:
                action='strengthen_bound_and_constraint_checks'; source='bound_check'
            record={'round':i,'budget':budget,'source':source,'recommended_action':action,'accepted':False,'reason':'Action is required before final packaging; implement the change and rerun the relevant gates.'}
            actions.append(record)
    unresolved = [a for a in actions if a.get('accepted') is False]
    status = 'warning' if unresolved else 'passed'
    report={'gate':'solution-improve','status':status,'rounds':rounds,'actions':actions,'generated_at':now_iso()}
    write_json(case_dir/'quality'/'improvements'/'solution_improvement_plan.json', report)
    return write_report(case_dir, 'solution_improvement_report.json', report)
