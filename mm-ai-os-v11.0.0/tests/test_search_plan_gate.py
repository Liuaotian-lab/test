from mmos.contracts.manager import ensure_case_scaffold
from mmos.kernel.jsonio import write_json
from mmos.problem_understanding import understand_problem
from mmos.academic_research_engine.search_orchestrator import orchestrate_academic_search, validate_search_plan


def test_academic_search_creates_layered_evidence_backed_queries(tmp_path):
    case_dir = tmp_path / 'case_search_gate'
    ensure_case_scaffold(case_dir)
    (case_dir / 'workspace' / 'problem_corpus.md').write_text(
        '问题1：建立炉温曲线模型，考虑温度、时间和传送带速度，并优化工艺参数。', encoding='utf-8'
    )
    write_json(case_dir / 'workspace' / 'problem_graph.json', {
        'questions': [{'question_id': 'Q1', 'title': '炉温曲线优化', 'source_excerpt': '建立炉温曲线模型，优化传送带速度。'}]
    })
    understand_problem(case_dir, strict=False)
    search = orchestrate_academic_search(case_dir, budget='full', strict=False)
    assert search['searches'][0]['total_queries'] > 0
    queries = search['searches'][0]['queries']
    assert all(q.get('query_id') for q in queries)
    assert all(q.get('purpose') for q in queries)
    assert any(q.get('purpose') == 'domain_model' for q in queries)
    gate = validate_search_plan(case_dir, strict=False)
    assert gate['gate'] == 'search_plan_gate'
    assert gate['status'] in {'passed', 'warning'}
