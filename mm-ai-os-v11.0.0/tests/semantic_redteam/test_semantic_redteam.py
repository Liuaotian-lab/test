from tests._v10_helpers import make_case, write_json
from mmos.semantic_redteam.gate import semantic_redteam


def test_semantic_redteam_surfaces_constraint_failure(tmp_path):
    case = make_case(tmp_path, ('Q3',))
    write_json(case/'workspace/constraints/official/constraint_ledger.json', {'case_id':case.name,'constraints':[{'constraint_id':'Q3_OPT','question_id':'Q3','constraint_type':'optimization_constraint','description':'minimum','depends_on':[],'required_solver_hooks':['s'],'required_validators':[],'required_negative_tests':[],'required_certificates':[],'claim_impact':['minimality'],'status':'active'}]})
    rep = semantic_redteam(case, all_questions=True)
    assert rep['status'] == 'failed'
    assert any(i['issue_type'] == 'constraint_coverage_failure' for i in rep['issues'])
