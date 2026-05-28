from tests._v10_helpers import make_case, add_valid_solution, add_validator, write_json
from mmos.final_gate_v2.final_gate import final_gate_v2


def test_final_gate_v2_blocks_missing_inherited_constraint_coverage(tmp_path):
    case = make_case(tmp_path, ('Q3',))
    add_valid_solution(case, 'Q3')
    add_validator(case, 'Q3')
    write_json(case/'workspace/constraints/official/constraint_ledger.json', {'case_id':case.name,'constraints':[{'constraint_id':'Q3_INHERIT','question_id':'Q3','constraint_type':'inherited_domain_constraint','description':'inherit collision','depends_on':['Q2_COLLISION'],'required_solver_hooks':['spiral'],'required_validators':[],'required_negative_tests':['pitch_below'],'required_certificates':['bracketing_certificate'],'claim_impact':['minimality'],'status':'active'}]})
    rep = final_gate_v2(case, root=None, strict=True)
    assert rep['status'] == 'failed'
    assert any(f.get('code') == 'MISSING_VALIDATOR' for f in rep['blocking_issues'])
