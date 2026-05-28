from __future__ import annotations
from pathlib import Path
from mmos.kernel.events import now_iso
from mmos.kernel.jsonio import read_json, write_json
from mmos.gates.solver_verify import verify_solver_result
from mmos.gates.report_consistency import report_consistency_check
from mmos.artifacts.outputs import validate_outputs, infer_question_id
from mmos.contracts.manager import check_contracts
from mmos.agent_protocols.tasks import agent_protocol_check
from mmos.agent_protocols.paper import paper_quality_check
# v7.0: capability_routing_check replaced by method_plan_check
from mmos.academic_research_engine.coverage_checker import check_coverage
from mmos.academic_research_engine.citation_manager import validate_citations
from mmos.semantic_checks.temporal import temporal_semantics_check
from mmos.semantic_checks.attachment_semantics import attachment_semantic_audit
from mmos.semantic_checks.model_fidelity import model_fidelity_check

# These gates are recomputed by final-gate-check.  Earlier releases only read
# pre-existing quality/*.json files, which allowed stale or forged gate reports
# to pass final packaging.  For unattended competition use, final gate must be a
# real verifier, not a manifest reader.

def _quality_gate_functions():
    from mmos.quality_oracle.model_maturity import model_maturity_check
    from mmos.quality_oracle.bound_checker import bound_check
    from mmos.tournament.solver_tournament import solver_tournament
    from mmos.quality_oracle.independent_verifier import independent_verify
    from mmos.quality_oracle.sensitivity import sensitivity_analysis
    from mmos.red_team.reviewer import red_team_review
    from mmos.optimism_control.optimism import (
        convergence_check,
        baseline_protocol_check,
        optimism_risk_check,
        optimism_debt_report,
    )
    from mmos.quality_oracle.improve import solution_improve
    from mmos.quality_oracle.oracle import quality_oracle
    return [
        ('model-maturity-check', model_maturity_check),
        ('bound-check', bound_check),
        ('solver-tournament', solver_tournament),
        ('independent-verify', independent_verify),
        ('sensitivity-analysis', sensitivity_analysis),
        ('red-team-review', red_team_review),
        ('convergence-check', convergence_check),
        ('baseline-protocol-check', baseline_protocol_check),
        ('optimism-risk-check', optimism_risk_check),
        ('optimism-debt-report', optimism_debt_report),
        ('solution-improve', solution_improve),
        ('quality-oracle-v2', quality_oracle),
    ]


def _required_questions(case_dir: Path) -> list[dict]:
    reg = read_json(case_dir / 'registry' / 'questions_registry.json', {'questions': []}) or {'questions': []}
    return [q for q in reg.get('questions', []) if q.get('required', True) is not False]


def _registered_required_outputs_by_question(case_dir: Path) -> dict[str, list[dict]]:
    reg = read_json(case_dir / 'registry' / 'outputs_registry.json', {'outputs': []}) or {'outputs': []}
    by_q: dict[str, list[dict]] = {}
    for out in reg.get('outputs', []) if isinstance(reg, dict) else []:
        if not out.get('required'):
            continue
        rel = out.get('path')
        qid = out.get('owner_question') or (infer_question_id(Path(rel)) if rel else None)
        if not qid:
            continue
        by_q.setdefault(str(qid), []).append(out)
    return by_q


def _status_ok(status: str | None, strict_warnings: bool) -> bool:
    if status in {'passed', 'ok'}:
        return True
    if status == 'warning' and not strict_warnings:
        return True
    return False


def _append_gate_failure(failures: list[dict], code: str, gate: str, report: dict) -> None:
    failures.append({
        'code': code,
        'gate': gate,
        'status': report.get('status'),
        'failures': report.get('failures'),
        'warnings': report.get('warnings') or report.get('findings') or report.get('debts'),
    })


def _run_quality_gates(case_dir: Path, strict_warnings: bool, failures: list[dict], gate_results: list[dict]) -> None:
    for gate, fn in _quality_gate_functions():
        try:
            report = fn(case_dir)
        except Exception as exc:  # final gate should fail closed on verifier exceptions
            report = {'gate': gate, 'status': 'failed', 'failures': [{'code': 'QUALITY_GATE_EXCEPTION', 'message': str(exc)}], 'warnings': []}
        gate_results.append({'gate': gate, 'status': report.get('status'), 'report': report})
        if not _status_ok(report.get('status'), strict_warnings):
            _append_gate_failure(failures, 'QUALITY_GATE_NOT_PASSED', gate, report)
        if gate == 'optimism-debt-report' and report.get('final_allowed') is False:
            failures.append({'code': 'OPTIMISM_DEBT_BLOCKS_FINAL', 'gate': gate, 'debts': report.get('debts', [])})
        if gate == 'quality-oracle-v2':
            if report.get('confidence') != 'high' and strict_warnings:
                failures.append({'code': 'QUALITY_ORACLE_CONFIDENCE_NOT_HIGH', 'gate': gate, 'confidence': report.get('confidence'), 'decision': report.get('decision')})
            if report.get('status') != 'passed' and strict_warnings:
                failures.append({'code': 'QUALITY_ORACLE_NOT_PASSED', 'gate': gate, 'status': report.get('status'), 'decision': report.get('decision')})


def final_gate_check(case_dir: Path, strict_warnings: bool = True, write: bool = True) -> dict:
    case_dir = Path(case_dir).resolve()
    failures: list[dict] = []
    warnings: list[dict] = []
    gate_results: list[dict] = []

    questions = _required_questions(case_dir)
    if not questions:
        failures.append({'code': 'NO_REQUIRED_QUESTIONS', 'message': 'questions_registry.json has no required questions.'})

    # v7.0: Method plan check replaces capability routing check.
    # Every method recommendation must be backed by academic search results.
    cov_report = check_coverage(case_dir, strict=False)
    gate_results.append({'gate': 'method-plan-check', 'status': cov_report.get('status'), 'report': cov_report})
    if not _status_ok(cov_report.get('status'), strict_warnings):
        _append_gate_failure(failures, 'METHOD_PLAN_CHECK_NOT_PASSED', 'method-plan-check', cov_report)

    cit_report = validate_citations(case_dir, strict=False)
    gate_results.append({'gate': 'citation-validation', 'status': cit_report.get('status'), 'report': cit_report})
    if not _status_ok(cit_report.get('status'), strict_warnings):
        _append_gate_failure(failures, 'CITATION_VALIDATION_NOT_PASSED', 'citation-validation', cit_report)

    # Semantic/fidelity gates catch failures that are invisible to file-existence gates.
    # Temporal semantics is blocking because unit/cycle mistakes can produce plausible
    # but wrong answers. Attachment/model fidelity are warning-tolerant at final gate
    # for backward compatibility, but first-prize-gate-check applies stricter caps.
    temporal_report = temporal_semantics_check(case_dir, strict=True)
    gate_results.append({'gate': 'temporal-semantics-check', 'status': temporal_report.get('status'), 'report': temporal_report})
    if not _status_ok(temporal_report.get('status'), strict_warnings):
        _append_gate_failure(failures, 'TEMPORAL_SEMANTICS_CHECK_NOT_PASSED', 'temporal-semantics-check', temporal_report)

    attach_report = attachment_semantic_audit(case_dir, strict=False)
    gate_results.append({'gate': 'attachment-semantic-audit', 'status': attach_report.get('status'), 'report': attach_report})
    if attach_report.get('status') == 'failed' and strict_warnings:
        _append_gate_failure(failures, 'ATTACHMENT_SEMANTIC_AUDIT_NOT_PASSED', 'attachment-semantic-audit', attach_report)

    fidelity_report = model_fidelity_check(case_dir, strict=False)
    gate_results.append({'gate': 'model-fidelity-check', 'status': fidelity_report.get('status'), 'report': fidelity_report})
    if fidelity_report.get('status') == 'failed' and strict_warnings:
        _append_gate_failure(failures, 'MODEL_FIDELITY_CHECK_NOT_PASSED', 'model-fidelity-check', fidelity_report)

    # Contract check is a blocking final gate. It is recomputed here so an agent
    # cannot run package-case after a stale or ignored failed contract check.
    contract_report = check_contracts(case_dir)
    gate_results.append({'gate': 'contract-check', 'status': contract_report.get('status'), 'report': contract_report})
    if not _status_ok(contract_report.get('status'), strict_warnings):
        _append_gate_failure(failures, 'CONTRACT_CHECK_NOT_PASSED', 'contract-check', contract_report)

    required_outputs_by_q = _registered_required_outputs_by_question(case_dir)
    for q in questions:
        qid = q.get('question_id') or q.get('id')
        if not qid:
            failures.append({'code': 'QUESTION_WITHOUT_ID', 'question': q})
            continue
        if q.get('status') not in {'activated', 'parsed', 'completed', 'done', 'running'}:
            warnings.append({'code': 'QUESTION_STATUS_NOT_ACTIVE', 'question_id': qid, 'status': q.get('status')})
        q_outputs = required_outputs_by_q.get(str(qid), [])
        if not q_outputs:
            failures.append({'code': 'NO_REQUIRED_OUTPUT_FOR_QUESTION', 'question_id': qid, 'message': 'Every required question must have at least one required registered output with owner_question/path namespace.'})
        sol = case_dir / 'results' / qid / 'outputs' / 'solution_real.json'
        if not sol.exists():
            failures.append({'code': 'MISSING_REAL_SOLUTION', 'question_id': qid, 'path': str(sol.relative_to(case_dir))})
            continue
        solver_report = verify_solver_result(sol)
        gate_results.append({'gate': 'solver-verify', 'question_id': qid, 'status': solver_report.get('status'), 'report': solver_report})
        if not _status_ok(solver_report.get('status'), strict_warnings):
            failures.append({'code': 'SOLVER_VERIFY_NOT_PASSED', 'question_id': qid, 'status': solver_report.get('status'), 'failures': solver_report.get('failures'), 'warnings': solver_report.get('warnings')})

    out_report = validate_outputs(case_dir, semantic=True, freshness=True)
    gate_results.append({'gate': 'output-validate', 'status': out_report.get('status'), 'report': out_report})
    if not _status_ok(out_report.get('status'), strict_warnings):
        _append_gate_failure(failures, 'OUTPUT_VALIDATE_NOT_PASSED', 'output-validate', out_report)

    rc_report = report_consistency_check(case_dir)
    gate_results.append({'gate': 'report-consistency-check', 'status': rc_report.get('status'), 'report': rc_report})
    if not _status_ok(rc_report.get('status'), strict_warnings):
        _append_gate_failure(failures, 'REPORT_CONSISTENCY_NOT_PASSED', 'report-consistency-check', rc_report)

    # Agent protocol gates are opt-in for backward compatibility. For official-contest
    # dry runs, set contracts/global/agent_protocol_contract.json required_for_final
    # flags to true; final-gate-check will then fail closed on missing parse-review,
    # verifier, paper, and figure artifacts.
    agent_contract = read_json(case_dir / 'contracts' / 'global' / 'agent_protocol_contract.json', {}) or {}
    required_flags = agent_contract.get('required_for_final') or {}
    if any(required_flags.values()):
        ap_report = agent_protocol_check(case_dir, strict=True)
        gate_results.append({'gate': 'agent-protocol-check', 'status': ap_report.get('status'), 'report': ap_report})
        if not _status_ok(ap_report.get('status'), strict_warnings):
            _append_gate_failure(failures, 'AGENT_PROTOCOL_CHECK_NOT_PASSED', 'agent-protocol-check', ap_report)
        if required_flags.get('paper_quality'):
            pq_report = paper_quality_check(case_dir, strict=True)
            gate_results.append({'gate': 'paper-quality-check', 'status': pq_report.get('status'), 'report': pq_report})
            if not _status_ok(pq_report.get('status'), strict_warnings):
                _append_gate_failure(failures, 'PAPER_QUALITY_CHECK_NOT_PASSED', 'paper-quality-check', pq_report)

    _run_quality_gates(case_dir, strict_warnings, failures, gate_results)

    submission_contract = read_json(case_dir / 'contracts' / 'global' / 'submission_contract.json', {}) or {}
    required_files = submission_contract.get('required_submission_files') or []
    for rel in required_files:
        if not (case_dir / rel).exists():
            failures.append({'code': 'SUBMISSION_CONTRACT_FILE_MISSING', 'path': rel})

    status = 'failed' if failures else ('warning' if warnings else 'passed')
    report = {
        'gate': 'final-gate-check',
        'status': status,
        'strict_warnings': strict_warnings,
        'final_allowed': status == 'passed',
        'failures': failures,
        'warnings': warnings,
        'gate_results': gate_results,
        'generated_at': now_iso(),
    }
    if write:
        write_json(case_dir / '.agent' / 'gate_reports' / 'final_gate_check.json', report)
        write_json(case_dir / 'final_outputs' / 'final_gate_check.json', report)
    return report
