from tests._v10_helpers import make_case, write_json
from mmos.dependencies.graph import dependency_check


def test_dependency_check_blocks_empty_inherited_edge(tmp_path):
    case = make_case(tmp_path, ('Q2','Q3'))
    write_json(case/'workspace/dependencies/official/question_dependency_graph.json', {
        'case_id': case.name,
        'edges': [{'from_question':'Q2','to_question':'Q3','dependency_type':'constraint_inheritance','blocking': True, 'required_hooks': [], 'required_validators': []}]
    })
    rep = dependency_check(case, all_questions=True)
    assert rep['status'] == 'failed'
    assert any(f['code'] == 'DEPENDENCY_WITHOUT_VALIDATOR_OR_HOOK' for f in rep['failures'])


def test_dependency_check_passes_validator_reuse_edge(tmp_path):
    case = make_case(tmp_path, ('Q2','Q3'))
    write_json(case/'workspace/dependencies/official/question_dependency_graph.json', {
        'case_id': case.name,
        'edges': [{'from_question':'Q2','to_question':'Q3','dependency_type':'validator_reuse','blocking': True, 'required_hooks': ['collision_detector'], 'required_validators': ['collision_free']}]
    })
    assert dependency_check(case, all_questions=True)['status'] == 'passed'
