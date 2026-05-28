from __future__ import annotations

from .commands_common import *
from .commands_common import _render_recommendation_md, render_run_report, _autopilot_step

def cmd_case_init(args, osp: OSPaths):
    dst = osp.case_dir(args.case)
    if dst.exists() and not args.force:
        raise SystemExit(f'case exists: {dst}; use --force')
    if dst.exists() and args.force:
        shutil.rmtree(dst)
    copytree_merge(osp.template_dir('case'), dst)
    result = ensure_case_scaffold(dst)
    # Replace __CASE_ID__ in template JSON where present
    for p in dst.rglob('*.json'):
        txt = p.read_text(encoding='utf-8')
        if '__CASE_ID__' in txt:
            p.write_text(txt.replace('__CASE_ID__', args.case), encoding='utf-8')
    print_json({'status': 'ok', 'case_dir': str(dst), 'scaffold': result})

def cmd_ingest(args, osp):
    case_dir = osp.case_dir(args.case)
    ensure_case_scaffold(case_dir)
    if getattr(args, 'unpack_archives', False):
        from mmos.ingestion.document_ingestor import unpack_archives
        unpack_archives(case_dir)
    print_json(build_problem_corpus(case_dir))

def cmd_parse(args, osp):
    ensure_case_scaffold(osp.case_dir(args.case))
    graph = build_problem_graph(osp.case_dir(args.case))
    # Automatically create draft contracts for parsed questions, but do not create engineering until activate.
    for q in graph.get('questions', []):
        build_question_contract(osp.case_dir(args.case), q.get('question_id'), qtype=q.get('type') or 'unknown', title=q.get('title'))
    print_json(graph)

def cmd_data_audit(args, osp):
    # data-audit is an explicit alias of ingest-documents; ingestion already emits data_manifest and data_audit.md.
    ensure_case_scaffold(osp.case_dir(args.case))
    print_json(build_problem_corpus(osp.case_dir(args.case)))

def cmd_problem_graph_build(args, osp):
    ensure_case_scaffold(osp.case_dir(args.case))
    print_json(build_problem_graph(osp.case_dir(args.case)))

def cmd_case_status(args, osp):
    case_dir = osp.case_dir(args.case)
    status = read_json(case_dir / '.agent' / 'question_status' / 'case_status.json', default={}) or {}
    status['questions_registry'] = registry_questions(case_dir)
    print_json(status)

def cmd_self_test(args, osp):
    print_json(run_self_test(osp.root, case_id=args.case, budget=args.budget))

def cmd_fixture_run(args, osp):
    print_json(run_fixtures(osp.root, budget=args.budget))

def cmd_backlog(args, osp):
    print_json(build_backlog(osp.case_dir(args.case)))
