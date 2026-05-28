from __future__ import annotations

from .commands_common import *
from .commands_common import _render_recommendation_md, render_run_report, _autopilot_step

def cmd_academic_search(args, osp):
    print_json(orchestrate_academic_search(osp.case_dir(args.case), question_id=args.question, budget=args.budget, strict=args.strict))

def cmd_method_match(args, osp):
    print_json(match_methods(osp.case_dir(args.case), question_id=args.question, strict=getattr(args, 'strict', True)))


def cmd_method_recommend(args, osp):
    # First run academic search, then match methods
    case_dir = osp.case_dir(args.case)
    sig = extract_problem_signature(case_dir, question_id=args.question)
    search = orchestrate_academic_search(case_dir, question_id=args.question, budget=args.budget, strict=False)
    matches = match_methods(case_dir, question_id=args.question, strict=False)
    # Write recommendations
    rec_dir = case_dir / 'workspace' / 'method_recommendations'
    rec_dir.mkdir(parents=True, exist_ok=True)
    for qid, match in matches.get('matches', {}).items():
        md = _render_recommendation_md(qid, match)
        (rec_dir / f'{qid}_recommendation.md').write_text(md, encoding='utf-8')
    print_json(matches)

def cmd_problem_parse_v2(args, osp):
    case_dir = osp.case_dir(args.case)
    ensure_case_scaffold(case_dir)
    graph = build_problem_graph(case_dir)
    for q in graph.get('questions', []):
        build_question_contract(case_dir, q.get('question_id'), qtype=q.get('type') or 'unknown', title=q.get('title'))
    print_json(graph)

def cmd_problem_signature_extract(args, osp):
    print_json(extract_problem_signature(osp.case_dir(args.case), question_id=args.question))

def cmd_problem_understand(args, osp):
    print_json(understand_problem(osp.case_dir(args.case), question_id=args.question, strict=args.strict))

def cmd_understanding_gate(args, osp):
    print_json(understanding_gate(osp.case_dir(args.case), question_id=args.question, strict=args.strict))

def cmd_search_plan_gate(args, osp):
    print_json(validate_search_plan(osp.case_dir(args.case), strict=args.strict))

def cmd_academic_search_v2(args, osp):
    # Alias for academic-search
    print_json(orchestrate_academic_search(osp.case_dir(args.case), question_id=args.question, budget=args.budget, strict=getattr(args, 'strict', True)))

def cmd_coverage_gap_analysis(args, osp):
    print_json(check_coverage(osp.case_dir(args.case), question_id=args.question, strict=getattr(args, 'strict', True)))

def cmd_method_plan_synthesize(args, osp):
    print_json(synthesize_method_plan(osp.case_dir(args.case), question_id=args.question, strict=getattr(args, 'strict', True)))

def cmd_method_plan_approve(args, osp):
    print_json(approve_method_plan(osp.case_dir(args.case), question_id=args.question, force=args.force))

def cmd_method_plan_check(args, osp):
    # Check coverage, citations, and plan quality
    case_dir = osp.case_dir(args.case)
    coverage = check_coverage(case_dir, question_id=args.question, strict=False)
    citations = validate_citations(case_dir, strict=False)
    out = {
        'status': 'passed' if coverage.get('status') == 'passed' and citations.get('status') == 'passed' else 'failed',
        'coverage': coverage,
        'citations': citations,
    }
    print_json(out)

def cmd_citation_validate(args, osp):
    print_json(validate_citations(osp.case_dir(args.case), strict=args.strict))

def cmd_semantic_audit(args, osp):
    print_json(semantic_audit(osp.case_dir(args.case), question_id=args.question, strict=args.strict))

def cmd_method_plan(args, osp):
    result = synthesize_method_plan(osp.case_dir(args.case), question_id=args.question, strict=False)
    citations = build_citation_list(osp.case_dir(args.case), question_id=args.question)
    result['citations'] = citations
    print_json(result)

def cmd_temporal_semantics_extract(args, osp):
    print_json(temporal_semantics_extract(osp.case_dir(args.case), question_id=args.question))

def cmd_temporal_semantics_check(args, osp):
    print_json(temporal_semantics_check(osp.case_dir(args.case), question_id=args.question, strict=args.strict))

def cmd_attachment_semantic_audit(args, osp):
    print_json(attachment_semantic_audit(osp.case_dir(args.case), strict=args.strict))

def cmd_model_fidelity_plan(args, osp):
    print_json(model_fidelity_plan(osp.case_dir(args.case), question_id=args.question))

def cmd_model_fidelity_check(args, osp):
    print_json(model_fidelity_check(osp.case_dir(args.case), question_id=args.question, strict=args.strict))
