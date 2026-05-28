from __future__ import annotations

from .commands_common import *
from .commands_common import _render_recommendation_md, render_run_report, _autopilot_step

def cmd_competition_autopilot(args, osp):
    case_dir = osp.case_dir(args.case)
    ensure_case_scaffold(case_dir)
    steps = []
    def run(name, fn, stop=False):
        try:
            result = fn()
        except Exception as exc:
            result = {'status': 'failed', 'error': str(exc)}
        steps.append({'step': name, 'status': result.get('status', 'ok') if isinstance(result, dict) else 'ok', 'result': result})
        if stop and isinstance(result, dict) and result.get('status') == 'failed':
            raise RuntimeError(name)
        return result
    try:
        run('ingest-documents', lambda: build_problem_corpus(case_dir), False)
        run('problem-parse', lambda: build_problem_graph(case_dir), False)
        run('problem-understand', lambda: understand_problem(case_dir, strict=False), False)
        run('understanding-gate', lambda: understanding_gate(case_dir, strict=False), False)
        run('academic-search', lambda: orchestrate_academic_search(case_dir, budget=args.budget, strict=False), False)
        run('method-match', lambda: match_methods(case_dir, strict=False), False)
        run('method-plan-synthesize', lambda: synthesize_method_plan(case_dir, strict=False), False)
        run('search-plan-gate', lambda: validate_search_plan(case_dir, strict=False), False)
        run('coverage-gap-analysis', lambda: check_coverage(case_dir, strict=False), False)
        run('question-activate-all-auto', lambda: activate_all_questions(case_dir, qtype='auto'), False)
        run('agent-task-generate', lambda: generate_agent_tasks(case_dir, phase='all', force=False), False)
        run('modeling-tournament', lambda: modeling_tournament(case_dir, target=args.target), False)
        if args.execute:
            run('case-run-flow', lambda: run_case_flow(case_dir, budget=args.budget, resume=False), False)
        run('claim-evidence-plan', lambda: claim_evidence_plan(case_dir), False)
        run('claim-evidence-check', lambda: claim_evidence_check(case_dir, strict=False), False)
        run('paper-argument-check', lambda: paper_argument_check(case_dir, strict=False), False)
        run('paper-evidence-check', lambda: paper_evidence_check(case_dir, strict=False), False)
        run('figure-argument-check', lambda: figure_argument_check(case_dir, strict=False), False)
        run('submission-gate-check', lambda: submission_gate_check(case_dir, strict_warnings=False), False)
        run('award-readiness-check', lambda: award_readiness_check(case_dir, target=args.target, strict_submission=False), False)
        run('repair-plan', lambda: repair_plan(case_dir), False)
        run('repair-task-generate', lambda: repair_task_generate(case_dir), False)
    except RuntimeError:
        pass
    failures = [s for s in steps if s.get('status') == 'failed']
    report = {'command':'competition-autopilot','case_id':args.case,'target':args.target,'status':'failed' if failures else 'passed','execute':args.execute,'steps':steps,'failure_count':len(failures),'note':'Reference-free autopilot does not use historical answer benchmarks.'}
    write_json(case_dir/'quality'/'competition_autopilot.json', report)
    print_json(report)

def cmd_contest_strategy(args, osp):
    print_json(build_contest_strategy(osp.case_dir(args.case), target=args.target, budget=args.budget, rounds=args.rounds))

def cmd_problem_intelligence(args, osp):
    print_json(problem_intelligence(osp.case_dir(args.case), target=args.target))

def cmd_modeling_tournament(args, osp):
    print_json(modeling_tournament(osp.case_dir(args.case), question_id=args.question, target=args.target))

def cmd_modeling_readiness(args, osp):
    print_json(modeling_readiness_check(osp.case_dir(args.case), question_id=args.question, strict=args.strict))

def cmd_solver_factory(args, osp):
    print_json(solver_factory(osp.case_dir(args.case), question_id=args.question, force=args.force))

def cmd_solver_benchmark(args, osp):
    print_json(solver_benchmark(osp.case_dir(args.case), question_id=args.question, strict=args.strict, min_variants=args.min_variants))

def cmd_verifier_factory(args, osp):
    print_json(verifier_factory(osp.case_dir(args.case), question_id=args.question, force=args.force, target=args.target))

def cmd_paper_plan(args, osp):
    print_json(paper_plan(osp.case_dir(args.case), target=args.target))

def cmd_figure_plan(args, osp):
    print_json(figure_plan(osp.case_dir(args.case), target=args.target, force=args.force))

def cmd_paper_polish(args, osp):
    print_json(paper_polish(osp.case_dir(args.case), target=args.target))

def cmd_judge_simulate(args, osp):
    print_json(judge_simulate(osp.case_dir(args.case), rounds=args.rounds, target=args.target))

def cmd_improvement_loop(args, osp):
    print_json(improvement_loop(osp.case_dir(args.case), rounds=args.rounds, target=args.target))

def cmd_first_prize_gate(args, osp):
    print_json(first_prize_gate_check(osp.case_dir(args.case), target_score=args.target_score, strict_final=args.strict_final))

def cmd_first_prize_autopilot(args, osp):
        print_json(first_prize_autopilot(osp.case_dir(args.case), execute=args.execute, budget=args.budget, rounds=args.rounds, package=args.package, continue_on_failure=args.continue_on_failure))

def cmd_case_autopilot(args, osp):
    case_dir = osp.case_dir(args.case)
    ensure_case_scaffold(case_dir)
    steps = []
    stop = not args.continue_on_failure
    final_package = None
    failed_early = False
    try:
        _autopilot_step('ingest-documents', lambda: build_problem_corpus(case_dir), steps, stop)
        _autopilot_step('problem-parse-v2', lambda: build_problem_graph(case_dir), steps, stop)
        _autopilot_step('problem-understand', lambda: understand_problem(case_dir, strict=False), steps, stop)
        _autopilot_step('understanding-gate', lambda: understanding_gate(case_dir, strict=False), steps, False)
        _autopilot_step('academic-search', lambda: orchestrate_academic_search(case_dir, budget=args.budget, strict=False), steps, stop)
        _autopilot_step('method-match', lambda: match_methods(case_dir, strict=False), steps, False)
        _autopilot_step('method-plan-synthesize', lambda: synthesize_method_plan(case_dir, strict=False), steps, False)
        _autopilot_step('problem-parse-review-template', lambda: problem_parse_review(case_dir, apply=False), steps, False)
        _autopilot_step('question-activate-all-auto', lambda: activate_all_questions(case_dir, qtype='auto'), steps, stop)
        _autopilot_step('agent-task-generate', lambda: generate_agent_tasks(case_dir, phase='all', force=False), steps, False)
        _autopilot_step('contract-check', lambda: check_contracts(case_dir), steps, stop)
        if args.execute:
            _autopilot_step('case-run-flow', lambda: run_case_flow(case_dir, budget=args.budget, resume=args.resume), steps, stop)
        else:
            steps.append({'step': 'case-run-flow', 'status': 'planned', 'result': {'status': 'planned', 'execute': False}})
        _autopilot_step('output-discover', lambda: discover_outputs(case_dir, write_draft=True), steps, stop)
        _autopilot_step('output-register-draft', lambda: register_output_draft(case_dir, accept=True), steps, stop)
        _autopilot_step('output-build', lambda: output_build(case_dir, all_required=True), steps, stop)
        _autopilot_step('output-validate', lambda: validate_outputs(case_dir, semantic=True, freshness=True), steps, stop)
        _autopilot_step('report-consistency-check', lambda: report_consistency_check(case_dir), steps, stop)
        _autopilot_step('paper-build', lambda: paper_build(case_dir, force=False), steps, False)
        _autopilot_step('paper-quality-check', lambda: paper_quality_check(case_dir, strict=False), steps, False)
        _autopilot_step('agent-protocol-check', lambda: agent_protocol_check(case_dir, strict=False), steps, False)
        final = _autopilot_step('final-gate-check', lambda: final_gate_check(case_dir, strict_warnings=not args.allow_warnings), steps, False)
        if args.package and final.get('status') == 'passed':
            final_package = _autopilot_step('package-case', lambda: package_case(case_dir, strict_warnings=not args.allow_warnings), steps, False)
    except RuntimeError:
        failed_early = True
    failures = [s for s in steps if s.get('status') == 'failed']
    report = {
        'command': 'case-autopilot',
        'case_id': args.case,
        'status': 'failed' if failures or failed_early else 'passed',
        'execute': args.execute,
        'budget': args.budget,
        'resume': args.resume,
        'package_requested': args.package,
        'package_result': final_package,
        'steps': steps,
        'failure_count': len(failures),
    }
    write_json(case_dir / 'quality' / 'unattended_autopilot_report.json', report)
    write_json(case_dir / '.agent' / 'gate_reports' / 'unattended_autopilot_report.json', report)
    print_json(report)
