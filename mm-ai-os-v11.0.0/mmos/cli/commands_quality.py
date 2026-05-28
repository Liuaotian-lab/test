from __future__ import annotations

from .commands_common import *
from .commands_common import _render_recommendation_md, render_run_report, _autopilot_step

def cmd_method_candidates(args, osp):
    print_json(method_candidates(osp.case_dir(args.case), question_id=args.question))

def cmd_model_maturity(args, osp):
    print_json(model_maturity_check(osp.case_dir(args.case), question_id=args.question))

def cmd_bound_check(args, osp):
    print_json(bound_check(osp.case_dir(args.case), question_id=args.question))

def cmd_independent_verify(args, osp):
    print_json(independent_verify(osp.case_dir(args.case), question_id=args.question, abs_tol=args.abs_tol, rel_tol=args.rel_tol))

def cmd_sensitivity(args, osp):
    print_json(sensitivity_analysis(osp.case_dir(args.case), question_id=args.question, budget=args.budget))

def cmd_solver_tournament(args, osp):
    print_json(solver_tournament(osp.case_dir(args.case), question_id=args.question, budget=args.budget, min_candidates=args.min_candidates))

def cmd_red_team(args, osp):
    print_json(red_team_review(osp.case_dir(args.case), question_id=args.question))

def cmd_quality_oracle(args, osp):
    print_json(quality_oracle(osp.case_dir(args.case), question_id=args.question))

def cmd_solution_improve(args, osp):
    print_json(solution_improve(osp.case_dir(args.case), question_id=args.question, rounds=args.rounds, budget=args.budget))

def cmd_optimism_risk(args, osp):
    print_json(optimism_risk_check(osp.case_dir(args.case), question_id=args.question))

def cmd_convergence(args, osp):
    print_json(convergence_check(osp.case_dir(args.case), question_id=args.question))

def cmd_baseline_protocol(args, osp):
    print_json(baseline_protocol_check(osp.case_dir(args.case), question_id=args.question))

def cmd_optimism_debt(args, osp):
    print_json(optimism_debt_report(osp.case_dir(args.case), question_id=args.question))

def cmd_quality_oracle_v2(args, osp):
    print_json(quality_oracle(osp.case_dir(args.case), question_id=args.question))

def cmd_solver_variant_verify(args, osp):
    print_json(solver_variant_verify(osp.case_dir(args.case), question_id=args.question, strict=args.strict))

def cmd_benchmark_compare(args, osp):
    result = {'status':'failed', 'error':'benchmark comparison is not included in the pure distribution; use semantic-audit, method-plan-check and final-gate instead.'}
    print_json(result)

def cmd_claim_evidence_plan(args, osp):
    print_json(claim_evidence_plan(osp.case_dir(args.case), question_id=args.question))

def cmd_claim_evidence_check(args, osp):
    print_json(claim_evidence_check(osp.case_dir(args.case), question_id=args.question, strict=args.strict))
