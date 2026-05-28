from __future__ import annotations
from pathlib import Path
from typing import Any

from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from mmos.kernel_gates.common import required_questions, status_from

LEVEL_RANK={'L0':0,'L1':1,'L2':2,'L3':3,'L4':4}
QUALITY_TO_LEVEL={
    'failed':'L0','exploratory':'L0','approximate':'L1','simulation_estimate':'L1','heuristic_feasible':'L1',
    'evaluated_best':'L2','local_optimal':'L2','exhaustive_best':'L3','certified_optimal':'L3','global_optimal':'L4'
}
QUALITY_RANK={'failed':0,'exploratory':0,'approximate':1,'simulation_estimate':1,'heuristic_feasible':1,'evaluated_best':2,'local_optimal':2,'exhaustive_best':3,'certified_optimal':3,'global_optimal':4}


def _compiled(case_dir: Path) -> dict[str, Any]:
    return read_json(Path(case_dir)/'workspace'/'dynamic_protocols'/'official'/'compiled_protocol.json', {}) or {}


def _qids(case_dir: Path) -> list[str]:
    return sorted((_compiled(case_dir).get('question_contracts') or {}).keys()) or required_questions(Path(case_dir)) or ['Q1']


def _solution(case_dir: Path, qid: str) -> dict[str, Any]:
    return read_json(Path(case_dir)/'results'/qid/'outputs'/'solution_real.json', {}) or read_json(Path(case_dir)/'engineering'/'results'/qid/'outputs'/f'solution_{qid}_real.json', {}) or {}


def _current_level(sol: dict[str, Any]) -> str:
    diag=sol.get('diagnostics') if isinstance(sol.get('diagnostics'),dict) else {}
    raw=sol.get('fidelity_level') or diag.get('fidelity_level') or diag.get('model_fidelity_level')
    if isinstance(raw,str) and raw[:2] in LEVEL_RANK:
        return raw[:2]
    q=sol.get('quality_level')
    return QUALITY_TO_LEVEL.get(str(q),'L0')


def _max_required(reqs: list[dict[str, Any]]) -> str:
    maxlvl='L0'
    for r in reqs:
        lvl=str(r.get('minimum_fidelity','L1'))[:2]
        if LEVEL_RANK.get(lvl,0)>LEVEL_RANK.get(maxlvl,0):
            maxlvl=lvl
    return maxlvl


def model_fidelity_plan_build(case_dir: Path, question_id: str | None = None, all_questions: bool = False) -> dict[str, Any]:
    case_dir=Path(case_dir)
    comp=_compiled(case_dir)
    failures=[]; plans=[]
    qids=[question_id] if question_id else _qids(case_dir)
    for qid in qids:
        contract=(comp.get('question_contracts') or {}).get(qid,{})
        reqs=contract.get('fidelity_requirements') or [{'component_id':'generic_model','minimum_fidelity':'L1','claim_limits':{'max_quality_level':'approximate'}}]
        plan={'question_id':qid,'fidelity_requirements':reqs,'minimum_case_fidelity':_max_required(reqs),'claim_limits':contract.get('claim_limits') or {'max_quality_level':'approximate','global_optimality_allowed':False}}
        plans.append(plan)
        write_json(case_dir/'contracts'/'questions'/qid/'model_fidelity_contract_dynamic.json', plan)
    report={'command':'model-fidelity-plan-build','status':status_from(failures,[]),'plans':plans,'failures':failures,'generated_at':now_iso()}
    write_json(case_dir/'quality'/'model_fidelity_plan_dynamic.json', report)
    return report


def dynamic_model_fidelity_check(case_dir: Path, question_id: str | None = None, strict: bool = True, write: bool = True) -> dict[str, Any]:
    case_dir=Path(case_dir)
    if not _compiled(case_dir):
        # Preserve compatibility: no dynamic protocol means this checker abstains with warning rather than inventing rules.
        report={'gate':'model-fidelity-check','status':'warning','strict':strict,'dynamic_protocol_present':False,'question_reports':[],'failures':[],'warnings':[{'code':'MISSING_COMPILED_PROTOCOL','message':'dynamic fidelity checker abstained'}],'generated_at':now_iso()}
        if write: write_json(case_dir/'quality'/'model_fidelity_check.json', report)
        return report
    plan=model_fidelity_plan_build(case_dir, question_id=question_id)
    failures=[]; warnings=[]; question_reports=[]
    for p in plan.get('plans',[]):
        qid=p['question_id']; sol=_solution(case_dir,qid)
        current=_current_level(sol)
        required=p.get('minimum_case_fidelity','L1')
        missing_solution=not bool(sol)
        if missing_solution:
            failures.append({'code':'MISSING_SOLUTION_FOR_FIDELITY_CHECK','question_id':qid})
        below=LEVEL_RANK.get(current,0)<LEVEL_RANK.get(str(required)[:2],1)
        if below and sol:
            failures.append({'code':'FIDELITY_BELOW_PROTOCOL_MINIMUM','question_id':qid,'current_fidelity':current,'required_fidelity':required})
        question_reports.append({'question_id':qid,'current_fidelity':current,'required_fidelity':required,'solution_present':bool(sol),'status':'failed' if missing_solution or below else 'passed','claim_limits':p.get('claim_limits')})
    report={'gate':'model-fidelity-check','status':status_from(failures,warnings),'strict':strict,'dynamic_protocol_present':True,'question_reports':question_reports,'failures':failures,'warnings':warnings,'generated_at':now_iso()}
    if write:
        write_json(case_dir/'quality'/'model_fidelity_check.json', report)
        write_json(case_dir/'.agent'/'gate_reports'/'model_fidelity_check.json', report)
    return report


def claim_limit_check(case_dir: Path, question_id: str | None = None, all_questions: bool = False) -> dict[str, Any]:
    case_dir=Path(case_dir); comp=_compiled(case_dir)
    failures=[]; warnings=[]; question_reports=[]
    qids=[question_id] if question_id else _qids(case_dir)
    for qid in qids:
        contract=(comp.get('question_contracts') or {}).get(qid,{})
        lim=contract.get('claim_limits') or {'max_quality_level':'approximate','global_optimality_allowed':False}
        maxq=str(lim.get('max_quality_level','approximate'))
        sol=_solution(case_dir,qid)
        ql=str(sol.get('quality_level','exploratory')) if sol else 'missing'
        optimal=bool(sol.get('optimal')) if sol else False
        if not sol:
            warnings.append({'code':'NO_SOLUTION_FOR_CLAIM_LIMIT_CHECK','question_id':qid})
        if sol and QUALITY_RANK.get(ql,0)>QUALITY_RANK.get(maxq,1):
            failures.append({'code':'QUALITY_LEVEL_EXCEEDS_PROTOCOL_CLAIM_LIMIT','question_id':qid,'quality_level':ql,'max_quality_level':maxq})
        if sol and (ql=='global_optimal' or optimal) and not lim.get('global_optimality_allowed',False):
            failures.append({'code':'GLOBAL_OR_OPTIMAL_CLAIM_NOT_ALLOWED_BY_PROTOCOL','question_id':qid,'quality_level':ql,'optimal':optimal})
        question_reports.append({'question_id':qid,'quality_level':ql,'max_quality_level':maxq,'optimal':optimal,'global_optimality_allowed':bool(lim.get('global_optimality_allowed',False))})
    report={'gate':'claim-limit-check','status':status_from(failures,warnings),'question_reports':question_reports,'failures':failures,'warnings':warnings,'generated_at':now_iso()}
    write_json(case_dir/'quality'/'claim_limit_check_report.json', report)
    return report


def fidelity_report(case_dir: Path) -> dict[str, Any]:
    case_dir=Path(case_dir)
    check=read_json(case_dir/'quality'/'model_fidelity_check.json', {}) or dynamic_model_fidelity_check(case_dir)
    claim=read_json(case_dir/'quality'/'claim_limit_check_report.json', {}) or claim_limit_check(case_dir)
    report={'status':status_from((check.get('failures') or [])+(claim.get('failures') or []),(check.get('warnings') or [])+(claim.get('warnings') or [])),'model_fidelity_check':check,'claim_limit_check':claim,'generated_at':now_iso()}
    write_json(case_dir/'quality'/'fidelity_report.json', report)
    return report
