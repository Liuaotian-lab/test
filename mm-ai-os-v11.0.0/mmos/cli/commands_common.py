from __future__ import annotations
import os
import argparse, json, shutil
from pathlib import Path
from mmos.kernel.paths import OSPaths, copytree_merge
from mmos.kernel.jsonio import write_json, read_json
from mmos.ingestion.document_ingestor import build_problem_corpus
from mmos.problem_graph.parser import build_problem_graph
from mmos.academic_research_engine.search_orchestrator import orchestrate_academic_search, validate_search_plan
from mmos.academic_research_engine.method_matcher import match_methods
from mmos.academic_research_engine.plan_builder import build_method_plan
from mmos.academic_research_engine.coverage_checker import check_coverage
from mmos.academic_research_engine.citation_manager import build_citation_list, validate_citations
from mmos.problem_signature.extractor import extract_problem_signature
from mmos.problem_understanding import understand_problem, understanding_gate
from mmos.method_plan.synthesizer import synthesize_method_plan, approve_method_plan
from mmos.semantic_checks.temporal import temporal_semantics_extract, temporal_semantics_check
from mmos.semantic_checks.attachment_semantics import attachment_semantic_audit
from mmos.semantic_checks.model_fidelity import model_fidelity_plan, model_fidelity_check
from mmos.semantic_checks.solver_variant import solver_variant_verify
from mmos.semantic_audit.auditor import semantic_audit
from mmos.claim_evidence.checker import claim_evidence_plan, claim_evidence_check
from mmos.semantic_audit.auditor import semantic_audit
from mmos.paper_excellence.checks import pdf_text_check, paper_argument_check, paper_evidence_check, figure_argument_check
from mmos.paper_excellence.evidence_engine import paper_readiness_gate, paper_evidence_graph, paper_argument_plan, figure_table_plan, appendix_code_build, appendix_code_check, paper_redteam_review, paper_repair_dispatch
from mmos.submission.gate import submission_gate_check
from mmos.award_readiness.checker import award_readiness_check
from mmos.repair_loop.repair import repair_plan, repair_task_generate
from mmos.paper_latex.latex import build_latex_source, compile_latex_pdf, paper_env_doctor
from mmos.workflow_runtime.runtime import run_question_flow, run_case_flow, run_stage, latest_run_dir
from mmos.artifacts.outputs import discover_outputs, validate_outputs
from mmos.artifacts.evidence import evidence_pack
from mmos.artifacts.package import register_output_draft, output_build, package_case
from mmos.gates.solver_verify import verify_solver_result
from mmos.gates.missing_info import missing_info_check
from mmos.gates.report_consistency import report_consistency_check
from mmos.feedback.backlog import build_backlog
from mmos.feedback.fixtures import run_fixtures
from mmos.feedback.selftest import run_self_test
from mmos.contracts.manager import ensure_case_scaffold, activate_question, activate_all_questions, build_question_contract, check_contracts, registry_questions, upsert_question

from mmos.quality_oracle.model_maturity import method_candidates, model_maturity_check
from mmos.quality_oracle.bound_checker import bound_check
from mmos.quality_oracle.independent_verifier import independent_verify
from mmos.quality_oracle.sensitivity import sensitivity_analysis
from mmos.quality_oracle.oracle import quality_oracle
from mmos.quality_oracle.improve import solution_improve
from mmos.tournament.solver_tournament import solver_tournament
from mmos.red_team.reviewer import red_team_review
from mmos.optimism_control.optimism import optimism_risk_check, convergence_check, baseline_protocol_check, optimism_debt_report
from mmos.artifacts.template_validators.fast_result import validate_fast_result_xlsx
from mmos.gates.final_gate import final_gate_check
from mmos.agent_protocols.tasks import generate_agent_tasks, agent_protocol_check
from mmos.agent_protocols.parse_review import problem_parse_review, apply_parse_review
from mmos.agent_protocols.verifiers import scaffold_verifier, run_verifiers, compare_verifiers
from mmos.agent_protocols.paper import paper_build, paper_quality_check

from mmos.contest_commander.strategy import build_contest_strategy, improvement_loop
from mmos.problem_intelligence.analyzer import problem_intelligence
from mmos.modeling_innovation.tournament import modeling_tournament, modeling_readiness_check
from mmos.solver_factory.factory import solver_factory, solver_benchmark
from mmos.agent_protocols.verifier_factory import verifier_factory
from mmos.paper_excellence.planner import paper_plan, figure_plan, paper_polish
from mmos.judge_simulation.simulator import judge_simulate
from mmos.gates.first_prize_gate import first_prize_gate_check
from mmos.contest_commander.autopilot import first_prize_autopilot



from mmos.chart_digitizer.digitizer import digitize_charts, chart_gaps
from mmos.chart_digitizer.qwen_vision_calibrator import calibrate_chart



OS_VERSION = '11.0.0'
OS_CODENAME = 'dynamic-protocol-certified-modeling-stable'
OS_RELEASE = '11.0.0-dynamic-protocol-certified-modeling-stable'

_LAST_EMITTED_JSON = None

def print_json(obj):
    global _LAST_EMITTED_JSON
    _LAST_EMITTED_JSON = obj
    print(json.dumps(obj, ensure_ascii=True, indent=2))

def _render_recommendation_md(qid: str, match: dict) -> str:
    lines = [f"# Method Recommendation: {qid}\n"]
    lines.append(f"## Methods Identified ({match.get('method_count', 0)})\n")
    for m in match.get('methods', []):
        lines.append(f"- **{m.get('name', 'Unknown')}**: {m.get('description', '')}")
        if m.get('source_title'):
            lines.append(f"  - Source: {m['source_title']}")
    lines.append(f"\n## Signature Context\n")
    lines.append(f"- Domain: {match.get('signature_summary', {}).get('domain', 'unknown')}")
    return '\n'.join(lines) + '\n'

def render_run_report(m):
    lines = [f"# Run Report: {m.get('case_id')}\n", f"- run_id: `{m.get('run_id')}`", f"- status: `{m.get('status')}`", f"- budget: `{m.get('budget_mode')}`", '', '| question | stage | status | return_code |', '|---|---|---:|---:|']
    for s in m.get('stages', []):
        lines.append(f"| {s.get('question_id')} | {s.get('stage')} | {s.get('status')} | {s.get('return_code')} |")
    return '\n'.join(lines) + '\n'

def _autopilot_step(name, fn, steps, stop_on_failure=True):
    try:
        result = fn()
    except Exception as exc:
        result = {'status': 'failed', 'error': str(exc)}
    status = result.get('status') if isinstance(result, dict) else None
    steps.append({'step': name, 'status': status or 'ok', 'result': result})
    if stop_on_failure and status == 'failed':
        raise RuntimeError(f'autopilot step failed: {name}')
    return result
