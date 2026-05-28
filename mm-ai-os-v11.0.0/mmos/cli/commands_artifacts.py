from __future__ import annotations

from .commands_common import *
from .commands_common import _render_recommendation_md, render_run_report, _autopilot_step

def cmd_output_discover(args, osp):
    print_json(discover_outputs(osp.case_dir(args.case), write_draft=args.write_draft))

def cmd_output_validate(args, osp):
    print_json(validate_outputs(osp.case_dir(args.case), semantic=args.semantic, freshness=args.freshness))

def cmd_output_register_draft(args, osp):
    print_json(register_output_draft(osp.case_dir(args.case), accept=args.accept))

def cmd_output_build(args, osp):
    print_json(output_build(osp.case_dir(args.case), all_required=args.all_required))

def cmd_package_case(args, osp):
    print_json(package_case(osp.case_dir(args.case), strict_warnings=not args.allow_warnings))

def cmd_solver_verify(args, osp):
    from mmos.kernel_gates.solver_verify import verify_solver_result as strict_verify_solver_result, verify_solver_results
    case_dir = osp.case_dir(args.case)
    strict = bool(getattr(args, 'strict', False) or getattr(args, 'strict_schema', False))
    if getattr(args, 'all', False):
        report = verify_solver_results(case_dir, strict=strict, root=osp.root)
        write_json(case_dir / '.agent' / 'solver_verify_reports' / 'all_solver_verify.json', report)
        print_json(report)
        return
    if not getattr(args, 'result', None):
        raise SystemExit('solver-verify requires --result PATH or --all')
    path = Path(args.result)
    if not path.is_absolute():
        candidates = [case_dir / path, osp.root / path, path]
        path = next((c for c in candidates if c.exists()), case_dir / path)
    report = strict_verify_solver_result(path, case_dir=case_dir, strict=strict, strict_schema=getattr(args, 'strict_schema', False), root=osp.root)
    qid = None
    try:
        data = read_json(path, {}) or {}
        qid = data.get('question_id')
    except Exception:
        pass
    out = case_dir / '.agent' / 'solver_verify_reports' / (f'{qid or path.stem}_solver_verify.json')
    write_json(out, report)
    print_json(report)


def cmd_placeholder_scan(args, osp):
    from mmos.kernel_gates.placeholder_scan import scan_placeholders
    print_json(scan_placeholders(osp.case_dir(args.case), root=osp.root, include_os=getattr(args, 'all', False)))


def cmd_constraint_test(args, osp):
    from mmos.kernel_gates.constraint_test import constraint_test
    print_json(constraint_test(osp.case_dir(args.case), question_id=getattr(args, 'question', None)))


def cmd_stale_output_check(args, osp):
    from mmos.kernel_gates.stale_output import stale_output_check
    print_json(stale_output_check(osp.case_dir(args.case), question_id=getattr(args, 'question', None)))

def cmd_missing_info(args, osp):
    print_json(missing_info_check(osp.case_dir(args.case), question_id=None if getattr(args, 'all', False) else args.question))

def cmd_evidence_pack(args, osp):
    if getattr(args, 'question', None):
        print_json(evidence_pack(osp.case_dir(args.case), question_id=args.question))
        return
    from mmos.evidence.claims import evidence_pack_case
    report = evidence_pack_case(osp.case_dir(args.case))
    if report.get('status') == 'failed':
        legacy = evidence_pack(osp.case_dir(args.case), question_id=None)
        report['legacy_evidence_pack'] = legacy
    print_json(report)

def cmd_report_consistency(args, osp):
    print_json(report_consistency_check(osp.case_dir(args.case), report_path=args.report, abs_tol=args.abs_tol, rel_tol=args.rel_tol))

def cmd_fast_result_validate(args, osp):
    print_json(validate_fast_result_xlsx(osp.case_dir(args.case), path=args.path))


def cmd_artifact_init_layout(args, osp):
    from mmos.core.artifacts import ensure_candidate_official_layout
    print_json(ensure_candidate_official_layout(osp.case_dir(args.case)))


def cmd_artifact_promote(args, osp):
    from mmos.core.artifacts import promote_artifact
    result = promote_artifact(
        osp.case_dir(args.case),
        args.source,
        args.destination,
        schema=args.schema,
        mirror_legacy=args.mirror_legacy,
    )
    print_json(result.to_dict())


def cmd_artifact_migrate_layout(args, osp):
    from mmos.core.artifacts import migrate_legacy_artifacts
    print_json(migrate_legacy_artifacts(osp.case_dir(args.case), overwrite=args.overwrite))


def cmd_agent_write_check(args, osp):
    from mmos.core.artifacts import evaluate_write_permission, default_allowed_files_manifest
    manifest_path = osp.case_dir(args.case) / '.agent' / 'allowed_files' / 'agent_write_policy.json'
    manifest = read_json(manifest_path, None) or default_allowed_files_manifest(args.case)
    print_json(evaluate_write_permission(args.path, manifest))
