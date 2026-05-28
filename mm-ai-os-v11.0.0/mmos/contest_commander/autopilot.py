from __future__ import annotations
from pathlib import Path
from typing import Any, Callable
from mmos.kernel.jsonio import write_json
from mmos.kernel.events import now_iso
from mmos.ingestion.document_ingestor import build_problem_corpus
from mmos.problem_graph.parser import build_problem_graph
from mmos.academic_research_engine.search_orchestrator import orchestrate_academic_search
from mmos.academic_research_engine.method_matcher import match_methods
from mmos.academic_research_engine.plan_builder import build_method_plan
from mmos.academic_research_engine.coverage_checker import check_coverage
from mmos.problem_signature.extractor import extract_problem_signature
from mmos.method_plan.synthesizer import synthesize_method_plan
from mmos.contracts.manager import ensure_case_scaffold, activate_all_questions, check_contracts
from mmos.agent_protocols.tasks import generate_agent_tasks
from mmos.agent_protocols.parse_review import problem_parse_review
from mmos.contest_commander.strategy import build_contest_strategy, improvement_loop
from mmos.problem_intelligence.analyzer import problem_intelligence
from mmos.modeling_innovation.tournament import modeling_tournament, modeling_readiness_check
from mmos.solver_factory.factory import solver_factory, solver_benchmark
from mmos.agent_protocols.verifier_factory import verifier_factory
from mmos.agent_protocols.verifiers import run_verifiers, compare_verifiers
from mmos.paper_excellence.planner import paper_plan, figure_plan, paper_polish
from mmos.agent_protocols.paper import paper_build, paper_quality_check
from mmos.workflow_runtime.runtime import run_case_flow
from mmos.artifacts.outputs import discover_outputs, validate_outputs
from mmos.artifacts.package import register_output_draft, output_build, package_case
from mmos.gates.report_consistency import report_consistency_check
from mmos.judge_simulation.simulator import judge_simulate
from mmos.gates.final_gate import final_gate_check
from mmos.gates.first_prize_gate import first_prize_gate_check


def _step(name: str, fn: Callable[[], dict[str, Any]], steps: list[dict[str, Any]], stop: bool) -> dict[str, Any]:
    try:
        result = fn()
    except Exception as exc:
        result = {'status': 'failed', 'error': str(exc)}
    status = result.get('status') if isinstance(result, dict) else 'ok'
    steps.append({'step': name, 'status': status or 'ok', 'result': result})
    if stop and status == 'failed':
        raise RuntimeError(name)
    return result


# v7.0: capability_dir parameter removed — search_templates are loaded from case root
def first_prize_autopilot(case_dir: Path, execute: bool = False, budget: str = 'full', rounds: int = 3, package: bool = False, continue_on_failure: bool = False) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    ensure_case_scaffold(case_dir)
    steps: list[dict[str, Any]] = []
    stop = not continue_on_failure
    package_result = None
    failed_early = False
    try:
        _step('ingest-documents', lambda: build_problem_corpus(case_dir), steps, stop)
        _step('problem-parse-v2', lambda: build_problem_graph(case_dir), steps, stop)
        _step('problem-parse-review-template', lambda: problem_parse_review(case_dir, apply=False), steps, False)
        _step('problem-signature-extract', lambda: extract_problem_signature(case_dir), steps, stop)
        _step('academic-search', lambda: orchestrate_academic_search(case_dir, budget=budget, strict=False), steps, stop)
        _step('method-match', lambda: match_methods(case_dir, strict=False), steps, False)
        _step('method-plan-synthesize', lambda: synthesize_method_plan(case_dir, strict=False), steps, False)
        _step('coverage-gap-analysis', lambda: check_coverage(case_dir, strict=False), steps, stop)
        _step('question-activate-all-auto', lambda: activate_all_questions(case_dir, qtype='auto'), steps, stop)
        _step('contest-strategy-plan', lambda: build_contest_strategy(case_dir, budget=budget, rounds=rounds), steps, stop)
        _step('problem-intelligence', lambda: problem_intelligence(case_dir), steps, stop)
        _step('agent-task-generate', lambda: generate_agent_tasks(case_dir, phase='all', force=False), steps, False)
        _step('modeling-tournament', lambda: modeling_tournament(case_dir), steps, stop)
        _step('modeling-readiness-check', lambda: modeling_readiness_check(case_dir, strict=False), steps, False)
        _step('solver-factory', lambda: solver_factory(case_dir), steps, False)
        _step('verifier-factory', lambda: verifier_factory(case_dir), steps, False)
        _step('paper-plan', lambda: paper_plan(case_dir), steps, False)
        _step('figure-plan', lambda: figure_plan(case_dir), steps, False)
        _step('contract-check', lambda: check_contracts(case_dir), steps, stop)
        if execute:
            _step('case-run-flow', lambda: run_case_flow(case_dir, budget=budget), steps, stop)
            _step('verifier-run', lambda: run_verifiers(case_dir), steps, False)
        else:
            steps.append({'step': 'case-run-flow', 'status': 'planned', 'result': {'status': 'planned', 'execute': False}})
        _step('solver-benchmark', lambda: solver_benchmark(case_dir, strict=False), steps, False)
        _step('verifier-compare', lambda: compare_verifiers(case_dir, strict=False), steps, False)
        _step('paper-build', lambda: paper_build(case_dir, force=False), steps, False)
        _step('paper-polish', lambda: paper_polish(case_dir), steps, False)
        _step('paper-quality-check', lambda: paper_quality_check(case_dir, strict=False), steps, False)
        _step('output-discover', lambda: discover_outputs(case_dir, write_draft=True), steps, stop)
        _step('output-register-draft', lambda: register_output_draft(case_dir, accept=True), steps, stop)
        _step('output-build', lambda: output_build(case_dir, all_required=True), steps, stop)
        _step('output-validate', lambda: validate_outputs(case_dir, semantic=True, freshness=True), steps, stop)
        _step('report-consistency-check', lambda: report_consistency_check(case_dir), steps, stop)
        _step('judge-simulate', lambda: judge_simulate(case_dir, rounds=rounds), steps, False)
        _step('improvement-loop', lambda: improvement_loop(case_dir, rounds=max(1, min(rounds, 3))), steps, False)
        _step('final-gate-check', lambda: final_gate_check(case_dir, strict_warnings=False), steps, False)
        fpg = _step('first-prize-gate-check', lambda: first_prize_gate_check(case_dir, strict_final=False), steps, False)
        if package and fpg.get('status') in {'passed','warning'}:
            package_result = _step('package-case', lambda: package_case(case_dir, strict_warnings=False), steps, False)
    except RuntimeError:
        failed_early = True
    failures = [s for s in steps if s.get('status') == 'failed']
    report = {
        'command': 'first-prize-autopilot',
        'case_id': case_dir.name,
        'status': 'failed' if failures or failed_early else 'passed',
        'execute': execute,
        'budget': budget,
        'rounds': rounds,
        'package_requested': package,
        'package_result': package_result,
        'failure_count': len(failures),
        'steps': steps,
        'generated_at': now_iso(),
    }
    write_json(case_dir / 'quality' / 'first_prize_autopilot_report.json', report)
    write_json(case_dir / '.agent' / 'gate_reports' / 'first_prize_autopilot_report.json', report)
    return report
