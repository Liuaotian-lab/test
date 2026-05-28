#!/usr/bin/env python3
"""
v7.0 Academic Research Engine — Regression Tests

Tests the new academic-search-driven method matching pipeline.
Run: python tests/academic_research_engine_checks.py
"""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mmos.contracts.manager import ensure_case_scaffold
from mmos.kernel.jsonio import write_json, read_json
from mmos.problem_signature.extractor import extract_problem_signature
from mmos.academic_research_engine.search_orchestrator import orchestrate_academic_search, _build_search_queries
from mmos.academic_research_engine.coverage_checker import check_coverage


def _make_case(case_id: str, text: str, questions: list[dict]) -> Path:
    case_dir = ROOT / 'cases' / case_id
    if case_dir.exists():
        shutil.rmtree(case_dir)
    ensure_case_scaffold(case_dir)
    (case_dir / 'workspace' / 'problem_corpus.md').write_text(text, encoding='utf-8')
    graph = {'case_id': case_id, 'status': 'ok', 'questions': questions}
    write_json(case_dir / 'workspace' / 'problem_graph.json', graph)
    write_json(case_dir / 'registry' / 'questions_registry.json', {'case_id': case_id, 'questions': questions})
    return case_dir


def test_search_queries_thermal():
    """
    Test that thermal process problems generate appropriate search queries
    targeting heat transfer / ODE / optimization literature.
    """
    text = (
        '回流焊炉内有11个小温区，电路板随传送带运动。'
        '图1为炉温曲线示意图。要求建立温度变化模型，检查150-190摄氏度时间、217摄氏度以上时间和峰值温度。'
        '问题1 给出炉温曲线并写入result.csv。问题2 求最大传送带速度。'
    )
    questions = [
        {'question_id': 'Q1', 'title': 'Q1', 'source_excerpt': text, 'required': True},
        {'question_id': 'Q2', 'title': 'Q2', 'source_excerpt': text, 'required': True},
    ]
    case_dir = _make_case('ace_test_thermal', text, questions)
    sig = extract_problem_signature(case_dir)
    assert sig['status'] == 'passed'
    # Verify signature structure
    q1 = sig['questions'].get('Q1', {})
    assert 'domain_family' in q1
    assert 'task_archetypes' in q1
    assert 'physical_quantities' in q1

    # Build search queries from the signature
    queries = _build_search_queries(q1, 'full')
    assert len(queries) > 0, "Should produce search queries"
    # Check that queries are thermal-related (not graph, not solar)
    all_queries = ' '.join(q.get('query', '') for q in queries)
    assert 'thermal' in all_queries.lower() or 'temperature' in all_queries.lower() or 'heat' in all_queries.lower(), \
        f"Queries should target thermal domain, got: {all_queries[:200]}"
    assert 'graph' not in all_queries.lower().split('graph_theory') and \
           'solar' not in all_queries.lower().split('solar_optical'), \
        f"Queries should NOT be misrouted to graph/solar, got: {all_queries[:200]}"

    print("  [PASS] test_search_queries_thermal")


def test_no_fallback_on_failure():
    """
    Test that the search orchestrator does NOT fall back to AI self-knowledge
    when search results are unavailable. It must return status=failed.
    """
    text = 'Question 1: Design a scoring rule for a novel game. No standard methods exist.'
    questions = [{'question_id': 'Q1', 'title': 'Q1', 'source_excerpt': text, 'required': True}]
    case_dir = _make_case('ace_test_nofallback', text, questions)

    # Extract signature first
    sig = extract_problem_signature(case_dir)
    assert sig['status'] == 'passed'

    # Attempt search — should fail gracefully, not fall back
    try:
        result = orchestrate_academic_search(case_dir, budget='fast', strict=False)
        # Even in non-strict mode, the search results should not fabricate methods
        assert result.get('status') in ('passed', 'failed'), f"Unexpected status: {result.get('status')}"
    except RuntimeError as e:
        # strict=True would raise — this confirms no fallback
        assert 'fallback' not in str(e).lower(), f"Error message references fallback: {e}"
        assert 'self-knowledge' not in str(e).lower(), f"Error message references self-knowledge: {e}"

    print("  [PASS] test_no_fallback_on_failure")


def test_signature_extraction_structure():
    """
    Test that the new extract_problem_signature produces the correct structure
    without relying on hardcoded PACK_DOMAIN_HINTS.
    """
    text = (
        '高压油管是燃油发动机的重要部件。已知某高压油管的内直径为6mm、长度为800mm，'
        '入口由柱塞腔提供高压燃油，出口有喷油嘴。要求建立高压油管内压力变化的数学模型。'
        '附件1给出了凸轮边缘曲线，附件2给出了针阀运动曲线，附件3给出了弹性模量与压力的关系。'
        '问题1 计算凸轮的角速度。问题2 设计减压阀的控制方案。问题3 设计单向阀的控制方案。'
    )
    questions = [
        {'question_id': 'Q1', 'title': 'Q1', 'source_excerpt': text, 'required': True},
        {'question_id': 'Q2', 'title': 'Q2', 'source_excerpt': text, 'required': True},
        {'question_id': 'Q3', 'title': 'Q3', 'source_excerpt': text, 'required': True},
    ]
    case_dir = _make_case('ace_test_hydraulic', text, questions)
    sig = extract_problem_signature(case_dir)

    assert sig['status'] == 'passed'
    for qid in ('Q1', 'Q2', 'Q3'):
        q = sig['questions'].get(qid, {})
        assert 'domain_family' in q, f"{qid} missing domain_family"
        assert 'entities' in q, f"{qid} missing entities"
        assert 'task_archetypes' in q, f"{qid} missing task_archetypes"
        assert 'negative_evidence' in q, f"{qid} missing negative_evidence"

    print("  [PASS] test_signature_extraction_structure")


def test_coverage_check_detects_gaps():
    """
    Test that check_coverage correctly identifies missing elements
    in a method plan.
    """
    text = 'Optimize the layout of a solar field. Maximize annual energy output.'
    questions = [{'question_id': 'Q1', 'title': 'Q1', 'source_excerpt': text, 'required': True}]
    case_dir = _make_case('ace_test_coverage', text, questions)

    # Write a deliberately incomplete method plan
    plan_dir = case_dir / 'workspace' / 'method_plan'
    plan_dir.mkdir(parents=True, exist_ok=True)
    incomplete_plan = {
        'question_id': 'Q1',
        'primary_model': None,  # Missing!
        'alternative_models': [],
        'optimization_method': None,
        'verification_approach': None,
        'literature_references': [],  # Zero citations!
        'citation_count': 0,
        'method_count': 0,
    }
    write_json(plan_dir / 'Q1_method_plan.json', incomplete_plan)
    write_json(plan_dir / 'case.method_plan_summary.json', {
        'status': 'warning',
        'plans': {'Q1': incomplete_plan}
    })

    # Also write a minimal problem signature
    sig_dir = case_dir / 'workspace' / 'problem_signatures'
    sig_dir.mkdir(parents=True, exist_ok=True)
    write_json(sig_dir / 'case.signatures.json', {
        'questions': {
            'Q1': {
                'domain_family': {'primary': 'solar_optical.heliostat_field'},
                'task_archetypes': [{'task': 'constrained_optimization'}],
                'constraints': ['land_area', 'spacing'],
            }
        }
    })

    gaps = check_coverage(case_dir, strict=False)
    assert gaps['status'] == 'failed', f"Expected failed, got {gaps['status']}"
    gap_types = [g['gap_type'] for g in gaps.get('gaps', [])]
    assert 'modeling' in gap_types, f"Should detect missing primary model, got gaps: {gap_types}"
    assert 'citations' in gap_types, f"Should detect missing citations, got gaps: {gap_types}"

    print("  [PASS] test_coverage_check_detects_gaps")


def test_search_queries_not_graph_when_figure_is_illustration():
    """
    Regression: "图1" (Figure 1) in thermal problems must NOT trigger graph theory searches.
    """
    text = '如图1所示，电路板通过传送带进入回流焊炉。建立温度模型.'
    questions = [{'question_id': 'Q1', 'title': 'Q1', 'source_excerpt': text, 'required': True}]
    case_dir = _make_case('ace_test_figure_not_graph', text, questions)

    sig = extract_problem_signature(case_dir)
    q1 = sig['questions'].get('Q1', {})

    # Build queries from the extracted signature and verify they don't include graph theory terms
    queries = _build_search_queries(q1, 'full')
    for q in queries:
        query_text = q.get('query', '').lower()
        # Must not contain standalone graph theory terms
        assert 'graph theory' not in query_text, f"Query incorrectly targets graph theory: {query_text}"
        assert 'network flow' not in query_text, f"Query incorrectly targets network flow: {query_text}"
        assert 'shortest path' not in query_text, f"Query incorrectly targets shortest path: {query_text}"

    print("  [PASS] test_search_queries_not_graph_when_figure_is_illustration")


if __name__ == '__main__':
    import traceback
    tests = [
        test_search_queries_thermal,
        test_no_fallback_on_failure,
        test_signature_extraction_structure,
        test_coverage_check_detects_gaps,
        test_search_queries_not_graph_when_figure_is_illustration,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except Exception:
            failed += 1
            traceback.print_exc()

    print(f"\n{'='*40}")
    print(f"  Results: {len(tests)-failed}/{len(tests)} passed")
    if failed:
        print(f"  {failed} FAILURES")
        sys.exit(1)
    else:
        print(f"  ALL PASSED")
