from __future__ import annotations

from .commands_common import *
from .commands_common import _render_recommendation_md, render_run_report, _autopilot_step

def cmd_pdf_text_check(args, osp):
    print_json(pdf_text_check(osp.case_dir(args.case)))

def cmd_paper_argument_check(args, osp):
    print_json(paper_argument_check(osp.case_dir(args.case), strict=args.strict))

def cmd_paper_evidence_check(args, osp):
    print_json(paper_evidence_check(osp.case_dir(args.case), strict=args.strict))

def cmd_figure_argument_check(args, osp):
    print_json(figure_argument_check(osp.case_dir(args.case), strict=args.strict))

def cmd_paper_readiness_gate(args, osp):
    print_json(paper_readiness_gate(osp.case_dir(args.case), target=args.target))

def cmd_paper_evidence_graph(args, osp):
    print_json(paper_evidence_graph(osp.case_dir(args.case), build=args.build))

def cmd_paper_argument_plan_v61(args, osp):
    print_json(paper_argument_plan(osp.case_dir(args.case), target=args.target))

def cmd_figure_table_plan(args, osp):
    print_json(figure_table_plan(osp.case_dir(args.case), target=args.target, force=args.force))

def cmd_appendix_code_build(args, osp):
    print_json(appendix_code_build(osp.case_dir(args.case), question_id=args.question, all_questions=args.all, force=args.force))

def cmd_appendix_code_check(args, osp):
    print_json(appendix_code_check(osp.case_dir(args.case), strict=args.strict))

def cmd_paper_redteam_review_v61(args, osp):
    print_json(paper_redteam_review(osp.case_dir(args.case), target=args.target))

def cmd_paper_repair_dispatch(args, osp):
    print_json(paper_repair_dispatch(osp.case_dir(args.case)))

def cmd_submission_gate(args, osp):
    print_json(submission_gate_check(osp.case_dir(args.case), strict_warnings=not args.allow_warnings))

def cmd_award_readiness(args, osp):
    print_json(award_readiness_check(osp.case_dir(args.case), target=args.target, strict_submission=args.strict_submission))

def cmd_repair_plan(args, osp):
    print_json(repair_plan(osp.case_dir(args.case)))

def cmd_repair_task_generate(args, osp):
    print_json(repair_task_generate(osp.case_dir(args.case)))

def cmd_latex_paper_build(args, osp):
    print_json(build_latex_source(osp.case_dir(args.case), force=args.force, template=getattr(args, 'template', 'cumcm_gold')))

def cmd_latex_paper_compile(args, osp):
    print_json(compile_latex_pdf(osp.case_dir(args.case), force=args.force, engine=args.engine))

def cmd_paper_env_doctor(args, osp):
    case_dir = osp.case_dir(args.case) if getattr(args, 'case', None) else None
    print_json(paper_env_doctor(osp.root, case_dir=case_dir))

def cmd_final_gate(args, osp):
    if getattr(args, 'strict', False):
        try:
            from mmos.final_gate_v2.final_gate import final_gate_v2
            print_json(final_gate_v2(osp.case_dir(args.case), root=osp.root, strict=True))
        except Exception:
            from mmos.kernel_gates.final_strict_gate import final_strict_gate_check
            print_json(final_strict_gate_check(osp.case_dir(args.case), root=osp.root))
        return
    print_json(final_gate_check(osp.case_dir(args.case), strict_warnings=not args.allow_warnings))

def cmd_package_submit(args, osp):
    print_json(package_case(osp.case_dir(args.case), strict_warnings=not args.allow_warnings))

def cmd_paper_build(args, osp):
    print_json(paper_build(osp.case_dir(args.case), force=args.force))

def cmd_paper_quality_check(args, osp):
    print_json(paper_quality_check(osp.case_dir(args.case), strict=args.strict))
