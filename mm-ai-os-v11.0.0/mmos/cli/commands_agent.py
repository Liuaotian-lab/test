from __future__ import annotations

from .commands_common import *
from .commands_common import _render_recommendation_md, render_run_report, _autopilot_step

def cmd_agent_task_generate(args, osp):
    print_json(generate_agent_tasks(osp.case_dir(args.case), question_id=args.question, phase=args.phase, force=args.force))

def cmd_agent_protocol_check(args, osp):
    print_json(agent_protocol_check(osp.case_dir(args.case), strict=args.strict, question_id=args.question))

def cmd_problem_parse_review(args, osp):
    print_json(problem_parse_review(osp.case_dir(args.case), apply=args.apply, require_passed=args.require_passed))

def cmd_problem_parse_apply_review(args, osp):
    print_json(apply_parse_review(osp.case_dir(args.case), require_passed=True))

def cmd_verifier_scaffold(args, osp):
    print_json(scaffold_verifier(osp.case_dir(args.case), question_id=args.question, force=args.force))

def cmd_verifier_run(args, osp):
    print_json(run_verifiers(osp.case_dir(args.case), question_id=args.question, abs_tol=args.abs_tol, rel_tol=args.rel_tol, timeout=args.timeout))

def cmd_verifier_compare(args, osp):
    print_json(compare_verifiers(osp.case_dir(args.case), question_id=args.question, strict=args.strict))
