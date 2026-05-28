from __future__ import annotations

from .commands_common import *
from .commands_common import _render_recommendation_md, render_run_report, _autopilot_step

def cmd_stage(args, osp):
    print_json(run_stage(osp.case_dir(args.case), args.question, args.stage, budget=args.budget, resume=args.resume))

def cmd_question_flow(args, osp):
    if not args.execute:
        print_json({'status':'planned', 'execute':False, 'question_id':args.question, 'stages':['validate','reduced','real','report'], 'message':'Add --execute to run stages.'})
        return
    print_json(run_question_flow(osp.case_dir(args.case), args.question, budget=args.budget, resume=args.resume))

def cmd_case_flow(args, osp):
    if not args.execute:
        questions = [q.get('question_id') or q.get('id') for q in registry_questions(osp.case_dir(args.case)) if q.get('required', True) is not False]
        print_json({'status':'planned', 'execute':False, 'required_questions':questions, 'stages':['validate','reduced','real','report'], 'message':'Add --execute to run stages.'})
        return
    print_json(run_case_flow(osp.case_dir(args.case), budget=args.budget, resume=args.resume))

def cmd_run_report(args, osp):
    case_dir = osp.case_dir(args.case)
    run_dir = latest_run_dir(case_dir) if args.latest else case_dir / 'runs' / args.run_id
    if not run_dir or not run_dir.exists():
        raise SystemExit('no run found')
    manifest = read_json(run_dir / 'run_manifest.json', {})
    md = render_run_report(manifest)
    out = case_dir / 'reports' / 'run_report.md'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding='utf-8')
    print_json({'status': 'ok', 'report': str(out), 'manifest': manifest})
