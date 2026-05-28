from mmos.contracts.manager import ensure_case_scaffold
from mmos.kernel.jsonio import write_json
from mmos.problem_signature.extractor import extract_problem_signature
from mmos.academic_research_engine.search_orchestrator import orchestrate_academic_search

def test_thermal_signature_bootstrap(tmp_path):
    case_dir = tmp_path / 'case_thermal'
    ensure_case_scaffold(case_dir)
    (case_dir / 'workspace' / 'problem_corpus.md').write_text('问题1：建立炉温曲线模型，考虑温度、时间和传送带速度，并优化工艺参数。', encoding='utf-8')
    write_json(case_dir / 'workspace' / 'problem_graph.json', {'questions': [{'question_id':'Q1','title':'炉温曲线优化','source_excerpt':'建立炉温曲线模型，优化传送带速度。'}]})
    sig = extract_problem_signature(case_dir)
    q1 = sig['questions']['Q1']
    assert q1['domain_family']['primary'] == 'physical_process.thermal_process'
    assert 'temperature' in q1['physical_quantities']
    search = orchestrate_academic_search(case_dir, strict=False)
    assert search['status'] == 'passed'
    assert search['searches'][0]['total_queries'] > 0
