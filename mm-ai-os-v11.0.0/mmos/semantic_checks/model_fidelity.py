from __future__ import annotations
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from mmos.quality_oracle.common import registry_questions

FIDELITY_ORDER={'L0_average_balance':0,'L1_lumped_pressure_ode':1,'L2_event_driven_geometry_ode':2,'L3_converged_verified_control':3,'L4_wave_or_pde_comparison':4}


def _case_domain(case_dir: Path) -> str:
    txt=''
    for p in [case_dir/'workspace'/'problem_corpus.md', case_dir/'workspace'/'problem_signatures'/'case.signatures.json']:
        if p.exists(): txt += p.read_text(encoding='utf-8', errors='ignore')
    if any(w in txt for w in ['高压油管','柱塞','针阀','减压阀','凸轮']):
        return 'hydraulic_pressure_control'
    if any(w in txt for w in ['炉温','温区','回焊炉']):
        return 'thermal_process'
    return 'generic'


def _required_for(domain: str, qid: str) -> dict[str, Any]:
    if domain == 'hydraulic_pressure_control':
        base={
            'Q1': ['density_pressure_relation','mass_balance_ode','valve_timing_semantics','steady_state_search'],
            'Q2': ['cam_plunger_geometry','plunger_chamber_pressure','needle_effective_area','event_driven_injection','time_step_convergence'],
            'Q3': ['two_injector_phase_optimization','relief_valve_threshold_strategy','alternative_relief_strategy','robustness_test'],
        }
        return {'required_fidelity':'L3_converged_verified_control','required_evidence':base.get(qid, ['model_specific_fidelity_evidence'])}
    return {'required_fidelity':'L2_event_driven_geometry_ode','required_evidence':['model_specific_fidelity_evidence','independent_verification','sensitivity_analysis']}


def model_fidelity_plan(case_dir: Path, question_id: str | None = None, write: bool = True) -> dict[str, Any]:
    case_dir=Path(case_dir).resolve(); domain=_case_domain(case_dir)
    qs=registry_questions(case_dir)
    if question_id: qs=[q for q in qs if (q.get('question_id') or q.get('id'))==question_id]
    plans=[]
    for q in qs:
        qid=q.get('question_id') or q.get('id')
        spec={'question_id':qid,'domain':domain,**_required_for(domain,qid)}
        plans.append(spec)
        if write:
            write_json(case_dir/'contracts'/'questions'/qid/'model_fidelity_contract.json', spec)
    report={'command':'model-fidelity-plan','status':'passed','domain':domain,'plans':plans,'generated_at':now_iso()}
    if write: write_json(case_dir/'quality'/'model_fidelity_plan.json', report)
    return report


def _solution_evidence(case_dir: Path, qid: str) -> tuple[str, set[str], dict[str, Any]]:
    sol=read_json(case_dir/'results'/qid/'outputs'/'solution_real.json', {}) or {}
    diag=sol.get('diagnostics') if isinstance(sol.get('diagnostics'), dict) else {}
    level=diag.get('model_fidelity_level') or diag.get('model_level') or sol.get('quality_level') or 'unknown'
    ev=set(diag.get('fidelity_evidence') or [])
    if diag.get('temporal_semantics'): ev.add('valve_timing_semantics')
    if diag.get('time_step_convergence'): ev.add('time_step_convergence')
    if diag.get('mass_balance_error') is not None: ev.add('mass_balance_ode')
    if diag.get('robustness_test'): ev.add('robustness_test')
    return str(level), ev, sol


def model_fidelity_check(case_dir: Path, question_id: str | None = None, strict: bool = True, write: bool = True) -> dict[str, Any]:
    case_dir=Path(case_dir).resolve()
    if (case_dir / 'workspace' / 'dynamic_protocols' / 'official' / 'compiled_protocol.json').exists():
        from mmos.fidelity.dynamic_fidelity import dynamic_model_fidelity_check
        return dynamic_model_fidelity_check(case_dir, question_id=question_id, strict=strict, write=write)
    plan=model_fidelity_plan(case_dir, question_id=question_id, write=True)
    failures=[]; warnings=[]; question_reports=[]; caps=[]
    for spec in plan.get('plans', []):
        qid=spec['question_id']
        level, ev, sol = _solution_evidence(case_dir, qid)
        required=set(spec.get('required_evidence') or [])
        missing=sorted(required-ev)
        numeric=FIDELITY_ORDER.get(level, -1)
        required_level=spec.get('required_fidelity')
        req_numeric=FIDELITY_ORDER.get(required_level, 2)
        cap=None
        if numeric < 0:
            cap='MAX_C_UNKNOWN_FIDELITY'
        elif numeric < req_numeric:
            cap='MAX_B_FIDELITY_BELOW_REQUIRED'
        if missing:
            cap=cap or 'MAX_B_MISSING_FIDELITY_EVIDENCE'
            msg={'code':'MISSING_FIDELITY_EVIDENCE','question_id':qid,'missing':missing,'current_level':level,'required_level':required_level}
            if strict: failures.append(msg)
            else: warnings.append(msg)
        if cap: caps.append({'question_id':qid,'cap':cap})
        question_reports.append({'question_id':qid,'current_fidelity':level,'required_fidelity':required_level,'evidence':sorted(ev),'missing':missing,'cap':cap})
    status='failed' if failures else ('warning' if warnings or caps else 'passed')
    report={'gate':'model-fidelity-check','status':status,'strict':strict,'question_reports':question_reports,'caps':caps,'failures':failures,'warnings':warnings,'generated_at':now_iso()}
    if write:
        write_json(case_dir/'quality'/'model_fidelity_check.json', report)
        write_json(case_dir/'.agent'/'gate_reports'/'model_fidelity_check.json', report)
    return report
