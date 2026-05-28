#!/usr/bin/env python3
from __future__ import annotations
import json, os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mmos.contracts.manager import ensure_case_scaffold, activate_question, check_contracts
from mmos.ingestion.document_ingestor import build_problem_corpus
from mmos.problem_graph.parser import build_problem_graph
from mmos.workflow_runtime.runtime import run_question_flow
from mmos.feedback.selftest import inject_selftest_contracts, inject_selftest_solver, inject_selftest_tournament_variants
from mmos.contest_commander.strategy import build_contest_strategy
from mmos.problem_intelligence.analyzer import problem_intelligence
from mmos.modeling_innovation.tournament import modeling_tournament, modeling_readiness_check
from mmos.solver_factory.factory import solver_factory, solver_benchmark
from mmos.agent_protocols.verifier_factory import verifier_factory
from mmos.agent_protocols.verifiers import run_verifiers, compare_verifiers
from mmos.paper_excellence.planner import paper_plan, figure_plan, paper_polish
from mmos.agent_protocols.paper import paper_build, paper_quality_check
from mmos.judge_simulation.simulator import judge_simulate
from mmos.contest_commander.strategy import improvement_loop
from mmos.artifacts.outputs import discover_outputs
from mmos.artifacts.package import register_output_draft, output_build
from mmos.artifacts.outputs import validate_outputs
from mmos.gates.report_consistency import report_consistency_check
from mmos.gates.first_prize_gate import first_prize_gate_check


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def reset_case(case_id: str) -> Path:
    case = ROOT / 'cases' / case_id
    shutil.rmtree(case, ignore_errors=True)
    ensure_case_scaffold(case)
    return case


def add_solver_run_variants(case: Path, qid: str) -> None:
    variants = {
        'baseline': {'objective_value': 0.96, 'robustness_score': 0.70, 'verification_score': 0.72, 'explainability_score': 0.80, 'risk_score': 0.25},
        'advanced': {'objective_value': 1.00, 'robustness_score': 0.88, 'verification_score': 0.90, 'explainability_score': 0.82, 'risk_score': 0.12},
    }
    for kind, payload in variants.items():
        payload = {
            'question_id': qid,
            'solver_kind': kind,
            'status': 'success',
            'feasible': True,
            'runtime_seconds': 1.0,
            **payload,
        }
        write_json(case / 'results' / qid / 'solver_runs' / kind / 'result.json', payload)


def cleanup_model_cards(case: Path, qid: str) -> None:
    for card in (case / 'workspace' / 'modeling' / qid / 'model_cards').glob('*.md'):
        text = card.read_text(encoding='utf-8')
        text = text.replace('Agent must refine', 'This refined artifact defines')
        text = text.replace('Replace generic card fields with domain-specific variables/objectives/constraints before first-prize gate.', 'Domain-specific variables/objectives/constraints have been bound for this acceptance fixture.')
        text += '\n## Fixture refinement evidence\n- variables: x and target_value\n- objective: minimize deviation from target\n- constraints: 0 <= x <= 2\n'
        card.write_text(text, encoding='utf-8')


def main() -> None:
    case = reset_case('fixture_first_prize_active_os')
    (case / 'data' / 'raw').mkdir(parents=True, exist_ok=True)
    (case / 'data' / 'raw' / 'problem.md').write_text(
        '问题一：统计分析输入数据，建立评价指标并输出 result1。\n'
        '问题二：建立优化模型，在 0 <= x <= 2 的约束下最大化评价值，输出 result2，并进行灵敏度分析。\n',
        encoding='utf-8'
    )
    build_problem_corpus(case)
    graph = build_problem_graph(case)
    assert len(graph.get('questions', [])) >= 2, graph
    for qid in ['Q1', 'Q2']:
        activate_question(case, qid, qtype='auto')
        inject_selftest_contracts(case, qid)
        inject_selftest_solver(case, qid)
        cc = check_contracts(case, qid)
        assert cc['status'] == 'passed', cc
        flow = run_question_flow(case, qid, budget='fast', resume=False)
        assert flow['status'] == 'passed', flow
        inject_selftest_tournament_variants(case, qid)

    strategy = build_contest_strategy(case, rounds=2)
    assert strategy['status'] == 'passed', strategy
    intel = problem_intelligence(case)
    assert intel['status'] == 'passed', intel
    mt = modeling_tournament(case)
    assert mt['status'] == 'passed', mt
    # Strict readiness should not accept untouched generic model cards.
    mr0 = modeling_readiness_check(case, strict=True)
    assert mr0['status'] == 'failed', mr0
    for qid in ['Q1', 'Q2']:
        cleanup_model_cards(case, qid)
    mr = modeling_readiness_check(case, strict=True)
    assert mr['status'] == 'passed', mr

    sf = solver_factory(case)
    assert sf['status'] == 'ok', sf
    for qid in ['Q1', 'Q2']:
        add_solver_run_variants(case, qid)
    sb = solver_benchmark(case, strict=True, min_variants=2)
    assert sb['status'] == 'passed', sb

    vf = verifier_factory(case)
    assert vf['status'] == 'ok', vf
    vr = run_verifiers(case)
    assert vr['status'] == 'passed', vr
    vc = compare_verifiers(case, strict=True)
    assert vc['status'] == 'passed', vc

    pp = paper_plan(case)
    assert pp['status'] == 'passed', pp
    fp = figure_plan(case)
    assert fp['status'] == 'planned', fp
    # Create placeholder figure files for the manifest; content is irrelevant to this structural gate.
    for fig in json.loads((case / 'paper' / 'figures_manifest.json').read_text(encoding='utf-8'))['figures']:
        (case / fig['path']).parent.mkdir(parents=True, exist_ok=True)
        (case / fig['path']).write_bytes(b'PNG acceptance fixture')
    pb = paper_build(case, force=True)
    assert pb['status'] == 'ok', pb
    polish = paper_polish(case)
    assert polish['status'] == 'ok', polish
    pq = paper_quality_check(case, strict=True)
    assert pq['status'] == 'passed', pq

    d = discover_outputs(case, write_draft=True)
    assert d['outputs'], d
    assert register_output_draft(case)['status'] == 'ok'
    assert output_build(case)['status'] == 'ok'
    ov = validate_outputs(case, semantic=True, freshness=True)
    assert ov['status'] == 'passed', ov
    rc = report_consistency_check(case)
    assert rc['status'] == 'passed', rc

    js = judge_simulate(case, rounds=2)
    assert js['grade'] in {'S', 'A', 'B'}, js
    imp = improvement_loop(case, rounds=1)
    assert imp['status'] == 'ok', imp
    fpg = first_prize_gate_check(case, target_score=65.0, strict_final=False)
    assert fpg['status'] in {'passed', 'warning'}, fpg
    assert fpg['first_prize_readiness']['grade'] in {'S', 'A', 'B', 'C'}, fpg
    assert (case / 'quality' / 'first_prize_gate_report.json').exists()
    print('first_prize_active_os_checks passed', flush=True); os._exit(0)


if __name__ == '__main__':
    main()
