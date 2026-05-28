from __future__ import annotations
from pathlib import Path
import shutil, time, json
from mmos.contracts.manager import ensure_case_scaffold, activate_question, check_contracts
from mmos.ingestion.document_ingestor import build_problem_corpus
from mmos.problem_graph.parser import build_problem_graph
# v7 semantic signature workflow
from mmos.academic_research_engine.search_orchestrator import orchestrate_academic_search
from mmos.problem_signature.extractor import extract_problem_signature
from mmos.gates.missing_info import missing_info_check
from mmos.workflow_runtime.runtime import run_question_flow, latest_run_dir
from mmos.gates.solver_verify import verify_solver_result
from mmos.artifacts.outputs import discover_outputs, validate_outputs
from mmos.artifacts.package import register_output_draft, output_build, package_case
from mmos.gates.report_consistency import report_consistency_check
from mmos.artifacts.evidence import evidence_pack
from mmos.quality_oracle.model_maturity import method_candidates, model_maturity_check
from mmos.quality_oracle.bound_checker import bound_check
from mmos.quality_oracle.independent_verifier import independent_verify
from mmos.quality_oracle.sensitivity import sensitivity_analysis
from mmos.tournament.solver_tournament import solver_tournament
from mmos.red_team.reviewer import red_team_review
from mmos.quality_oracle.improve import solution_improve
from mmos.quality_oracle.oracle import quality_oracle
from mmos.optimism_control.optimism import optimism_risk_check, convergence_check, baseline_protocol_check, optimism_debt_report
from mmos.kernel.jsonio import write_json


PASS_STATUSES = {'ok', 'passed'}


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def inject_selftest_contracts(case_dir: Path, qid: str) -> None:
    qdir = case_dir/'contracts'/'questions'/qid
    _write(qdir/'variable_registry.json', {
        'case_id': case_dir.name,
        'question_id': qid,
        'variables': [
            {'name':'x', 'role':'decision', 'description':'single nonnegative decision variable for the smoke optimization model', 'domain':'x >= 0'},
            {'name':'target_value', 'role':'input', 'description':'known reference target value used for validation', 'value':1.0},
        ]
    })
    _write(qdir/'constraint_registry.json', {
        'case_id': case_dir.name,
        'question_id': qid,
        'hard_constraints': [
            {'name':'nonnegative_x', 'expression':'x >= 0', 'source':'selftest_problem_statement'},
            {'name':'upper_smoke_bound', 'expression':'x <= 2', 'source':'selftest_problem_statement'},
        ],
        'constraints': []
    })
    _write(qdir/'validation_contract.json', {
        'case_id': case_dir.name,
        'question_id': qid,
        'validators': ['numeric_metric_present', 'nonnegative_x_checked', 'independent_recompute_within_5pct'],
        'checks': [
            {'name':'objective_value_numeric', 'required':True},
            {'name':'constraints_checked_true', 'required':True},
            {'name':'reduced_real_consistency', 'required':True, 'rel_tol':0.05},
        ]
    })


def inject_selftest_solver(case_dir: Path, qid: str) -> None:
    solver = case_dir/'engineering'/'questions'/qid/'solve.py'
    solver.write_text('''from __future__ import annotations
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def solve(stage: str, budget: str, context: dict) -> dict:
    value = 1.0 if stage == "real" else 0.98
    return {
        "question_id": context.get("question_id", "Q1"),
        "status": "success",
        "stage": stage,
        "method": "selftest_competition_solver",
        "solver_name": "selftest_competition_solver",
        "quality_level": "evaluated_best",
        "created_at": now_iso(),
        "objective_value": value,
        "metrics": {"feasibility_margin": 1.0, "validation_score": value},
        "diagnostics": {
            "fallback_used": False,
            "budget": budget,
            "constraints_checked": True,
            "model_level": "L4",
            "multi_solver": True,
            "solver_variants": ["primary_real_solver", "baseline_variant", "perturbed_variant"],
            "independent_verification": {"method": "reduced_real_consistency", "relative_tolerance": 0.05},
            "sensitivity_parameters": [
                {"name": "target_value", "relative_delta": 0.05, "status": "stable"},
                {"name": "upper_smoke_bound", "relative_delta": 0.10, "status": "stable"}
            ],
            "sensitivity_analysis": {"status": "passed", "policy_changed": False},
            "comparison_protocol": {
                "same_metric_definition": True,
                "same_sampling_strategy": True,
                "same_domain_scope": True,
                "same_weighting_policy": True
            },
            "warnings": []
        }
    }
''', encoding='utf-8')



def inject_selftest_method_plan(case_dir: Path, qid: str) -> None:
    _write(case_dir/'workspace'/'method_plan'/'official'/'case.method_plan_summary.json', {
        'case_id': case_dir.name,
        'plans': {
            qid: {
                'primary_model': 'selftest deterministic bounded scalar optimization',
                'alternative_models': ['closed_form_baseline', 'perturbed_consistency_solver'],
                'optimization_method': 'direct evaluation with feasibility check',
                'verification_approach': 'independent reduced-real consistency check',
                'citation_count': 1,
                'citations': [{'id': 'selftest_internal_protocol', 'title': 'Internal smoke protocol'}]
            }
        }
    })

def inject_selftest_tournament_variants(case_dir: Path, qid: str) -> None:
    variant_dir = case_dir/'results'/qid/'tournament'
    base = {
        'question_id': qid,
        'status': 'success',
        'stage': 'real',
        'method': 'selftest_variant_solver',
        'quality_level': 'heuristic_feasible',
        'diagnostics': {'fallback_used': False, 'constraints_checked': True, 'model_level': 'L3'}
    }
    for name, value in [('baseline_variant', 0.97), ('perturbed_variant', 0.995)]:
        payload = dict(base)
        payload.update({'solver_name': name, 'objective_value': value, 'metrics': {'validation_score': value}})
        _write(variant_dir/f'{name}.json', payload)


def run_self_test(os_root: Path, case_id: str = 'selftest_v53_fixed', budget: str = 'fast') -> dict:
    t0=time.perf_counter(); os_root=Path(os_root).resolve(); case_dir=os_root/'cases'/case_id
    if case_dir.exists(): shutil.rmtree(case_dir)
    tpl=os_root/'templates'/'case'
    if tpl.exists(): shutil.copytree(tpl, case_dir)
    ensure_case_scaffold(case_dir)
    raw=case_dir/'data'/'raw'; raw.mkdir(parents=True, exist_ok=True)
    (raw/'problem.md').write_text('问题 1：建立一个简单优化模型，输出结构化结果。要求变量 x 满足 0 <= x <= 2，并使目标值尽量接近 1.0；需要给出可行方案、约束检验、独立验证和结果报告。\n', encoding='utf-8')
    steps=[]

    def step(name, fn, require_status: bool = True):
        st=time.perf_counter(); status='ok'; err=None; result=None
        try:
            result=fn()
            if require_status and isinstance(result, dict) and result.get('status') not in PASS_STATUSES:
                status='failed'; err=f"returned status={result.get('status')}"
        except Exception as e:
            status='failed'; err=str(e)
        steps.append({'name':name,'status':status,'duration_sec':round(time.perf_counter()-st,3),'error':err,'result_status': result.get('status') if isinstance(result, dict) else None})
        if status=='failed':
            raise RuntimeError(f'{name} failed: {err}')
        return result

    step('ingest-documents', lambda: build_problem_corpus(case_dir), require_status=False)
    step('problem-parse', lambda: build_problem_graph(case_dir), require_status=False)
    step('problem-signature-extract', lambda: extract_problem_signature(case_dir), require_status=False)
    step('academic-search', lambda: orchestrate_academic_search(case_dir, budget='fast', strict=False), require_status=False)
    step('question-activate', lambda: activate_question(case_dir,'Q1',qtype='auto'))
    inject_selftest_contracts(case_dir, 'Q1')
    inject_selftest_solver(case_dir, 'Q1')
    step('contract-check', lambda: check_contracts(case_dir,'Q1'))
    step('missing-info-check', lambda: missing_info_check(case_dir,'Q1'))
    step('method-candidates', lambda: method_candidates(case_dir))
    inject_selftest_method_plan(case_dir, 'Q1')
    step('question-run-flow', lambda: run_question_flow(case_dir,'Q1',budget=budget,resume=False))
    inject_selftest_tournament_variants(case_dir, 'Q1')
    step('solver-verify', lambda: verify_solver_result(case_dir/'results'/'Q1'/'outputs'/'solution_real.json'))
    step('output-discover', lambda: discover_outputs(case_dir, write_draft=True), require_status=False)
    step('output-register-draft', lambda: register_output_draft(case_dir, accept=True))
    step('output-build', lambda: output_build(case_dir, all_required=True))
    step('output-validate', lambda: validate_outputs(case_dir, semantic=True, freshness=True))
    step('report-consistency-check', lambda: report_consistency_check(case_dir))
    step('model-maturity-check', lambda: model_maturity_check(case_dir))
    step('solver-tournament', lambda: solver_tournament(case_dir,budget=budget))
    step('independent-verify', lambda: independent_verify(case_dir))
    step('bound-check', lambda: bound_check(case_dir))
    step('sensitivity-analysis', lambda: sensitivity_analysis(case_dir,budget=budget))
    step('red-team-review', lambda: red_team_review(case_dir))
    step('convergence-check', lambda: convergence_check(case_dir))
    step('baseline-protocol-check', lambda: baseline_protocol_check(case_dir))
    step('optimism-risk-check', lambda: optimism_risk_check(case_dir))
    step('optimism-debt-report', lambda: optimism_debt_report(case_dir))
    step('solution-improve', lambda: solution_improve(case_dir, rounds=2, budget=budget))
    step('evidence-pack', lambda: evidence_pack(case_dir))
    step('quality-oracle', lambda: quality_oracle(case_dir))
    step('package-case', lambda: package_case(case_dir))
    required=[
        case_dir/'.agent', case_dir/'contracts', case_dir/'.agent'/'task_cards'/'Q1_task_card.md',
        case_dir/'contracts'/'questions'/'Q1'/'problem_spec.json', case_dir/'results'/'Q1'/'outputs'/'solution_real.json',
        case_dir/'quality'/'surrogate_quality_report.json', case_dir/'final_outputs'/'final_gate_check.json', case_dir/'package'/'final_submission.zip'
    ]
    missing=[str(p.relative_to(case_dir)) for p in required if not p.exists()]
    status='failed' if missing else 'passed'
    report={'status':status,'case_id':case_id,'case_dir':str(case_dir),'budget':budget,'duration_sec':round(time.perf_counter()-t0,3),'missing':missing,'steps':steps,'run_dir':str(latest_run_dir(case_dir) or '')}
    write_json(os_root/'tests'/'self_test_report.json', report)
    return report
