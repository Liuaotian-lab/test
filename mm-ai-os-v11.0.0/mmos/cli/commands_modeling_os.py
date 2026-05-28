from __future__ import annotations
from .commands_common import print_json


def cmd_experiment_record(args, osp):
    from mmos.experiment.record import experiment_record, experiment_record_all
    if getattr(args, 'all', False):
        print_json(experiment_record_all(osp.case_dir(args.case)))
        return
    if not getattr(args, 'question', None):
        raise SystemExit('experiment-record requires --question QID or --all')
    print_json(experiment_record(osp.case_dir(args.case), args.question))


def cmd_experiment_pack(args, osp):
    from mmos.experiment.pack import experiment_pack
    print_json(experiment_pack(osp.case_dir(args.case)))


def cmd_evidence_pack_v2(args, osp):
    from mmos.evidence.claims import evidence_pack_case
    print_json(evidence_pack_case(osp.case_dir(args.case)))


def cmd_claim_check(args, osp):
    from mmos.evidence.claim_check import claim_check
    print_json(claim_check(osp.case_dir(args.case), all_claims=getattr(args, 'all', False)))


def cmd_skill_list(args, osp):
    from mmos.skills_runtime.loader import list_skills
    print_json(list_skills(osp.root))


def cmd_skill_show(args, osp):
    from mmos.skills_runtime.loader import show_skill
    print_json(show_skill(osp.root, args.skill))


def cmd_skill_run(args, osp):
    from mmos.skills_runtime.runner import run_skill
    print_json(run_skill(osp.root, osp.case_dir(args.case), args.skill))


def cmd_skill_check(args, osp):
    from mmos.skills_runtime.runner import check_skill
    print_json(check_skill(osp.root, osp.case_dir(args.case), args.skill))


def cmd_routing_check(args, osp):
    from mmos.routing.checker import routing_check
    print_json(routing_check(osp.case_dir(args.case), all_routes=getattr(args, 'all', False)))


def cmd_routing_promote(args, osp):
    from mmos.routing.checker import routing_promote
    print_json(routing_promote(osp.case_dir(args.case), all_routes=getattr(args, 'all', False)))


def cmd_validator_build(args, osp):
    if getattr(args, 'from_source', None) == 'compiled-protocol':
        args.from_compiled_protocol = True
    if getattr(args, 'from_compiled_protocol', False):
        from mmos.dynamic_tests.builder import dynamic_validator_build
        print_json(dynamic_validator_build(osp.case_dir(args.case), question_id=getattr(args, 'question', None), all_questions=getattr(args, 'all', False)))
    else:
        from mmos.validators.runner import validator_build
        q = getattr(args, 'question', None)
        if not q:
            raise ValueError('validator-build requires --question unless --from-compiled-protocol is used')
        print_json(validator_build(osp.case_dir(args.case), q))


def cmd_validator_test(args, osp):
    from mmos.validators.runner import validator_test
    print_json(validator_test(osp.case_dir(args.case), question_id=getattr(args, 'question', None)))


def cmd_negative_test(args, osp):
    from mmos.validators.negative_tests import negative_test
    print_json(negative_test(osp.case_dir(args.case), question_id=getattr(args, 'question', None)))


def cmd_capability_list(args, osp):
    from mmos.capabilities.loader import capability_list
    print_json(capability_list(osp.root))


def cmd_capability_show(args, osp):
    from mmos.capabilities.loader import capability_show
    print_json(capability_show(osp.root, args.capability))


def cmd_context_build(args, osp):
    from mmos.context.budget import context_build
    print_json(context_build(osp.case_dir(args.case), args.task))


def cmd_context_check(args, osp):
    from mmos.context.budget import context_check
    print_json(context_check(osp.case_dir(args.case)))


def cmd_context_compact(args, osp):
    from mmos.context.budget import context_compact
    print_json(context_compact(osp.case_dir(args.case)))


def cmd_quality_review(args, osp):
    from mmos.quality_protocol.review import quality_review
    print_json(quality_review(osp.case_dir(args.case), all_questions=getattr(args, 'all', False)))


def cmd_red_team_gate(args, osp):
    from mmos.quality_protocol.red_team import red_team_gate
    print_json(red_team_gate(osp.case_dir(args.case), all_questions=getattr(args, 'all', False)))


def cmd_model_readiness_gate(args, osp):
    from mmos.quality_protocol.model_readiness import model_readiness_gate
    print_json(model_readiness_gate(osp.case_dir(args.case), question_id=getattr(args, 'question', None), all_questions=getattr(args, 'all', False)))


def cmd_verified_candidate_comparison(args, osp):
    from mmos.quality_protocol.model_readiness import verified_candidate_comparison
    print_json(verified_candidate_comparison(osp.case_dir(args.case), question_id=getattr(args, 'question', None)))


def cmd_mcp_safe_check(args, osp):
    from mmos.mcp_safety.policy import evaluate_mcp_safe_call
    print_json(evaluate_mcp_safe_call(osp.case_dir(args.case), tool_class=args.tool_class, target=args.target, query=args.query, source_url=args.source_url, used_for=args.used_for))


# v10 Constraint-certified OS commands

def cmd_constraint_ledger_build(args, osp):
    from mmos.constraints.ledger import build_constraint_ledger
    print_json(build_constraint_ledger(osp.case_dir(args.case), force=getattr(args, 'force', False)))


def cmd_constraint_ledger_check(args, osp):
    from mmos.constraints.ledger import check_constraint_ledger
    print_json(check_constraint_ledger(osp.case_dir(args.case)))


def cmd_constraint_coverage_check(args, osp):
    from mmos.constraints.coverage import constraint_coverage_check
    print_json(constraint_coverage_check(osp.case_dir(args.case), all_questions=getattr(args, 'all', False)))


def cmd_constraint_promote(args, osp):
    from mmos.constraints.ledger import promote_constraint_ledger
    print_json(promote_constraint_ledger(osp.case_dir(args.case)))


def cmd_dependency_graph_build(args, osp):
    from mmos.dependencies.graph import build_dependency_graph
    print_json(build_dependency_graph(osp.case_dir(args.case), force=getattr(args, 'force', False)))


def cmd_dependency_check(args, osp):
    from mmos.dependencies.graph import dependency_check
    print_json(dependency_check(osp.case_dir(args.case), all_questions=getattr(args, 'all', False)))


def cmd_dependency_report(args, osp):
    from mmos.kernel.jsonio import read_json
    p = osp.case_dir(args.case) / 'workspace' / 'dependencies' / 'reports' / 'dependency_check_report.json'
    print_json(read_json(p, {'status': 'failed', 'failures': [{'code': 'MISSING_DEPENDENCY_REPORT'}]}))


def cmd_certificate_build(args, osp):
    if getattr(args, 'from_source', None) == 'certificate-plan':
        from mmos.dynamic_certificates.planner import certificate_build_from_plan
        print_json(certificate_build_from_plan(osp.case_dir(args.case), question_id=getattr(args, 'question', None), all_questions=getattr(args, 'all', False)))
    else:
        from mmos.certificates.checker import build_certificate
        print_json(build_certificate(osp.case_dir(args.case), question_id=getattr(args, 'question', None)))


def cmd_certificate_check(args, osp):
    from mmos.certificates.checker import certificate_check
    print_json(certificate_check(osp.case_dir(args.case), question_id=getattr(args, 'question', None), all_questions=getattr(args, 'all', False)))


def cmd_certificate_report(args, osp):
    from mmos.kernel.jsonio import read_json
    p = osp.case_dir(args.case) / 'quality' / 'certificate_check_report.json'
    print_json(read_json(p, {'status': 'failed', 'failures': [{'code': 'MISSING_CERTIFICATE_REPORT'}]}))


def cmd_validator_adequacy_check(args, osp):
    from mmos.validator_adequacy.adequacy import validator_adequacy_check
    print_json(validator_adequacy_check(osp.case_dir(args.case), question_id=getattr(args, 'question', None), all_questions=getattr(args, 'all', False)))


def cmd_adversarial_test_build(args, osp):
    from mmos.validator_adequacy.adequacy import adversarial_test_build
    print_json(adversarial_test_build(osp.case_dir(args.case), question_id=getattr(args, 'question', None)))


def cmd_adversarial_test_run(args, osp):
    from mmos.validator_adequacy.adequacy import adversarial_test_run
    print_json(adversarial_test_run(osp.case_dir(args.case), question_id=getattr(args, 'question', None)))


def cmd_semantic_redteam(args, osp):
    from mmos.semantic_redteam.gate import semantic_redteam
    print_json(semantic_redteam(osp.case_dir(args.case), all_questions=getattr(args, 'all', False)))


def cmd_missing_constraint_probe(args, osp):
    from mmos.semantic_redteam.gate import missing_constraint_probe
    print_json(missing_constraint_probe(osp.case_dir(args.case), all_questions=getattr(args, 'all', False)))


def cmd_overclaim_check(args, osp):
    from mmos.semantic_redteam.gate import overclaim_check
    print_json(overclaim_check(osp.case_dir(args.case), all_questions=getattr(args, 'all', False)))


def cmd_model_risk_register(args, osp):
    from mmos.semantic_redteam.gate import model_risk_register
    print_json(model_risk_register(osp.case_dir(args.case), all_questions=getattr(args, 'all', False)))


def cmd_model_risk_check(args, osp):
    from mmos.semantic_redteam.gate import model_risk_check
    print_json(model_risk_check(osp.case_dir(args.case)))


def cmd_independent_verify_protocol(args, osp):
    from mmos.independent_verification.protocol import independent_verification_protocol
    print_json(independent_verification_protocol(osp.case_dir(args.case), question_id=getattr(args, 'question', None), all_questions=getattr(args, 'all', False)))


def cmd_verified_candidate_comparison_v2(args, osp):
    from mmos.independent_verification.protocol import verified_candidate_comparison_v2
    print_json(verified_candidate_comparison_v2(osp.case_dir(args.case)))


def cmd_final_gate_v2(args, osp):
    from mmos.final_gate_v2.final_gate import final_gate_v2
    print_json(final_gate_v2(osp.case_dir(args.case), root=osp.root, strict=getattr(args, 'strict', True)))


def cmd_prompt_profile_list(args, osp):
    from mmos.agent_protocol.runtime import prompt_profile_list
    print_json(prompt_profile_list(osp.root))


def cmd_prompt_profile_show(args, osp):
    from mmos.agent_protocol.runtime import prompt_profile_show
    print_json(prompt_profile_show(osp.root, args.profile))


def cmd_task_card_build(args, osp):
    from mmos.agent_protocol.runtime import task_card_build
    print_json(task_card_build(osp.case_dir(args.case), role=args.role, question_id=getattr(args, 'question', None), profile=getattr(args, 'profile', 'modeling_agent_strict_v10'), phase=getattr(args, 'phase', 'full_case')))


def cmd_failure_ledger_add(args, osp):
    from mmos.agent_protocol.runtime import failure_ledger_add
    print_json(failure_ledger_add(osp.case_dir(args.case), command=getattr(args, 'command', 'unknown'), return_code=getattr(args, 'return_code', 1), stdout_excerpt=getattr(args, 'stdout', ''), stderr_excerpt=getattr(args, 'stderr', ''), root_cause=getattr(args, 'root_cause', 'unknown')))


def cmd_repair_check_v10(args, osp):
    from mmos.agent_protocol.runtime import repair_check
    print_json(repair_check(osp.case_dir(args.case)))


def cmd_migrate_case_to_v10(args, osp):
    from mmos.constraints.ledger import build_constraint_ledger
    from mmos.dependencies.graph import build_dependency_graph
    case_dir = osp.case_dir(args.case)
    a = build_constraint_ledger(case_dir, force=False)
    b = build_dependency_graph(case_dir, force=False)
    print_json({'status': 'passed' if a.get('status') == 'passed' and b.get('status') == 'passed' else 'failed', 'mode': args.mode, 'steps': [a, b]})


def cmd_case_policy_set(args, osp):
    from mmos.kernel.jsonio import write_json
    p = osp.case_dir(args.case) / 'quality' / 'case_policy.json'
    data = {'strictness': args.strictness}
    write_json(p, data)
    print_json({'status': 'passed', 'path': str(p), 'policy': data})

# v11 Dynamic Protocol OS commands

def cmd_problem_type_infer(args, osp):
    from mmos.protocol_synthesis.type_infer import problem_type_infer
    print_json(problem_type_infer(osp.case_dir(args.case)))


def cmd_capability_atom_match(args, osp):
    from mmos.protocol_synthesis.atom_matcher import capability_atom_match
    print_json(capability_atom_match(osp.root, osp.case_dir(args.case)))


def cmd_protocol_synthesize(args, osp):
    from mmos.protocol_synthesis.protocol_synthesizer import protocol_synthesize
    print_json(protocol_synthesize(osp.root, osp.case_dir(args.case)))


def cmd_protocol_lint(args, osp):
    from mmos.protocol_synthesis.protocol_linter import protocol_lint
    print_json(protocol_lint(osp.case_dir(args.case)))


def cmd_protocol_redteam(args, osp):
    from mmos.protocol_synthesis.protocol_redteam import protocol_redteam
    print_json(protocol_redteam(osp.case_dir(args.case)))


def cmd_protocol_compile(args, osp):
    from mmos.protocol_synthesis.protocol_compiler import protocol_compile
    print_json(protocol_compile(osp.case_dir(args.case)))


def cmd_dynamic_protocol_gate(args, osp):
    from mmos.protocol_synthesis.gate import dynamic_protocol_gate
    print_json(dynamic_protocol_gate(osp.case_dir(args.case), strict=getattr(args, 'strict', True)))


def cmd_negative_test_build(args, osp):
    if getattr(args, 'from_source', None) == 'compiled-protocol':
        args.from_compiled_protocol = True
    from mmos.dynamic_tests.builder import negative_test_build
    print_json(negative_test_build(osp.case_dir(args.case), question_id=getattr(args, 'question', None), all_questions=getattr(args, 'all', False)))


def cmd_mutation_test_build(args, osp):
    if getattr(args, 'from_source', None) == 'compiled-protocol':
        args.from_compiled_protocol = True
    from mmos.dynamic_tests.builder import mutation_test_build
    print_json(mutation_test_build(osp.case_dir(args.case), question_id=getattr(args, 'question', None), all_questions=getattr(args, 'all', False)))


def cmd_validator_adequacy_check_v2(args, osp):
    from mmos.dynamic_tests.builder import validator_adequacy_check_v2
    print_json(validator_adequacy_check_v2(osp.case_dir(args.case), question_id=getattr(args, 'question', None), all_questions=getattr(args, 'all', False)))


def cmd_model_fidelity_plan_build(args, osp):
    if getattr(args, 'from_source', None) == 'compiled-protocol':
        args.from_compiled_protocol = True
    from mmos.fidelity.dynamic_fidelity import model_fidelity_plan_build
    print_json(model_fidelity_plan_build(osp.case_dir(args.case), question_id=getattr(args, 'question', None), all_questions=getattr(args, 'all', False)))


def cmd_claim_limit_check(args, osp):
    from mmos.fidelity.dynamic_fidelity import claim_limit_check
    print_json(claim_limit_check(osp.case_dir(args.case), question_id=getattr(args, 'question', None), all_questions=getattr(args, 'all', False)))


def cmd_fidelity_report(args, osp):
    from mmos.fidelity.dynamic_fidelity import fidelity_report
    print_json(fidelity_report(osp.case_dir(args.case)))


def cmd_certificate_plan_synthesize(args, osp):
    from mmos.dynamic_certificates.planner import certificate_plan_synthesize
    print_json(certificate_plan_synthesize(osp.case_dir(args.case), question_id=getattr(args, 'question', None), all_questions=getattr(args, 'all', False)))


def cmd_certificate_check_v2(args, osp):
    from mmos.dynamic_certificates.planner import certificate_check_v2
    print_json(certificate_check_v2(osp.case_dir(args.case), question_id=getattr(args, 'question', None), all_questions=getattr(args, 'all', False)))


def cmd_claim_certificate_bind(args, osp):
    from mmos.dynamic_certificates.planner import claim_certificate_bind
    print_json(claim_certificate_bind(osp.case_dir(args.case), question_id=getattr(args, 'question', None), all_questions=getattr(args, 'all', False)))


def cmd_output_template_infer(args, osp):
    from mmos.output_schema.dynamic_output_schema import output_template_infer
    print_json(output_template_infer(osp.case_dir(args.case)))


def cmd_output_schema_synthesize(args, osp):
    from mmos.output_schema.dynamic_output_schema import output_schema_synthesize
    print_json(output_schema_synthesize(osp.case_dir(args.case)))


def cmd_output_schema_check(args, osp):
    from mmos.output_schema.dynamic_output_schema import output_schema_check
    print_json(output_schema_check(osp.case_dir(args.case)))


def cmd_workbook_schema_validate(args, osp):
    from mmos.output_schema.dynamic_output_schema import workbook_schema_validate
    print_json(workbook_schema_validate(osp.case_dir(args.case), all_required=getattr(args, 'all_required', False)))


def cmd_independent_solver_synthesize(args, osp):
    from mmos.heterogeneous_verification.runner import independent_solver_synthesize
    print_json(independent_solver_synthesize(osp.case_dir(args.case), question_id=getattr(args, 'question', None), all_questions=getattr(args, 'all', False)))


def cmd_heterogeneous_verify(args, osp):
    from mmos.heterogeneous_verification.runner import heterogeneous_verify
    print_json(heterogeneous_verify(osp.case_dir(args.case), question_id=getattr(args, 'question', None), all_questions=getattr(args, 'all', False)))


def cmd_discrepancy_report(args, osp):
    from mmos.heterogeneous_verification.runner import discrepancy_report
    print_json(discrepancy_report(osp.case_dir(args.case), question_id=getattr(args, 'question', None), all_questions=getattr(args, 'all', False)))


def cmd_gate_escape_risk_check(args, osp):
    from mmos.os_diagnostics.reports import gate_escape_risk_check
    print_json(gate_escape_risk_check(osp.case_dir(args.case)))


def cmd_capability_gap_matrix(args, osp):
    from mmos.os_diagnostics.reports import capability_gap_matrix
    print_json(capability_gap_matrix(osp.case_dir(args.case), root=osp.root))


def cmd_protocol_reuse_suggest(args, osp):
    from mmos.os_diagnostics.reports import protocol_reuse_suggest
    print_json(protocol_reuse_suggest(osp.case_dir(args.case)))


def cmd_os_improvement_report(args, osp):
    from mmos.os_diagnostics.reports import os_improvement_report
    print_json(os_improvement_report(osp.case_dir(args.case), root=osp.root))


def cmd_final_gate_v3(args, osp):
    from mmos.final_gate_v3.final_gate import final_gate_v3
    print_json(final_gate_v3(osp.case_dir(args.case), root=osp.root, strict=getattr(args, 'strict', True)))
