from mmos.contracts.manager import ensure_case_scaffold
from mmos.kernel.jsonio import write_json
from mmos.problem_understanding import understand_problem, understanding_gate


def test_problem_understanding_writes_evidence_and_gate(tmp_path):
    case_dir = tmp_path / 'case_understanding'
    ensure_case_scaffold(case_dir)
    (case_dir / 'workspace' / 'problem_corpus.md').write_text(
        '问题1：建立炉温曲线模型，考虑温度、时间和传送带速度。要求峰值温度不超过250摄氏度，并确定最优传送带速度。附件一给出实验数据。',
        encoding='utf-8'
    )
    write_json(case_dir / 'workspace' / 'problem_graph.json', {
        'questions': [{'question_id': 'Q1', 'title': '炉温曲线优化', 'source_excerpt': '建立炉温曲线模型，峰值温度不超过250摄氏度，确定最优传送带速度。'}]
    })
    result = understand_problem(case_dir, strict=False)
    assert result['status'] in {'passed', 'warning'}
    assert (case_dir / 'workspace' / 'problem_understanding' / 'evidence_index.json').exists()
    assert (case_dir / 'workspace' / 'problem_understanding' / 'final_problem_signature.json').exists()
    gate = understanding_gate(case_dir, strict=False)
    assert gate['gate'] == 'understanding_gate'
    assert gate['status'] in {'passed', 'warning'}


def test_understanding_gate_rejects_missing_evidence_in_agent_candidate(tmp_path):
    case_dir = tmp_path / 'case_bad_agent'
    ensure_case_scaffold(case_dir)
    (case_dir / 'workspace' / 'problem_corpus.md').write_text('问题1：预测未来交通流量。', encoding='utf-8')
    write_json(case_dir / 'workspace' / 'problem_graph.json', {'questions': [{'question_id': 'Q1', 'title': '交通预测', 'source_excerpt': '预测未来交通流量。'}]})
    # Missing evidence_ids must be caught even when supplied by an external Agent.
    write_json(case_dir / 'workspace' / 'problem_understanding' / 'agent_candidate_signature.json', {
        'questions': {
            'Q1': {
                'goal': {'claim': '预测未来交通流量', 'confidence': 0.9},
                'task_archetypes': [{'task': 'prediction', 'confidence': 0.9}],
                'variables': [],
                'constraints': [],
                'data_requirements': [],
                'required_outputs': [{'type': 'prediction_result', 'confidence': 0.8}]
            }
        }
    })
    result = understand_problem(case_dir, strict=False)
    assert result['gate']['status'] == 'failed'
    assert result['gate']['blocking_issue_count'] > 0
