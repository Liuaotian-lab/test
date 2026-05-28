from __future__ import annotations

from .commands_common import *
from .commands_common import _render_recommendation_md, render_run_report, _autopilot_step

def cmd_question_activate(args, osp):
    if getattr(args, 'all', False) or args.question == 'all':
        print_json(activate_all_questions(osp.case_dir(args.case), qtype=args.type, required=args.required, force=args.force))
        return
    if not args.question:
        raise SystemExit('question-activate requires --question QID or --all')
    print_json(activate_question(osp.case_dir(args.case), args.question, qtype=args.type, title=args.title, required=args.required, force=args.force))

def cmd_contract_build(args, osp):
    case_dir = osp.case_dir(args.case)
    from_source = getattr(args, 'from_source', None)
    if from_source == 'compiled-protocol':
        args.from_compiled_protocol = True
    if getattr(args, 'all', False) or getattr(args, 'from_compiled_protocol', False):
        questions = registry_questions(case_dir)
        results = []
        for q in questions:
            qid = q.get('question_id') or q.get('id')
            if qid:
                results.append(build_question_contract(case_dir, qid, qtype=args.type or q.get('type') or 'auto', title=args.title or q.get('title'), force=args.force))
        failures = [r for r in results if isinstance(r, dict) and r.get('status') == 'failed']
        print_json({'status': 'failed' if failures else 'passed', 'mode': 'all', 'from_compiled_protocol': bool(getattr(args, 'from_compiled_protocol', False)), 'contracts': results})
        return
    if not args.question:
        raise SystemExit('contract-build requires --question QID, --all, or --from compiled-protocol')
    print_json(build_question_contract(case_dir, args.question, qtype=args.type, title=args.title, force=args.force))

def cmd_contract_check(args, osp):
    print_json(check_contracts(osp.case_dir(args.case), question_id=None if getattr(args, 'all', False) else args.question))
