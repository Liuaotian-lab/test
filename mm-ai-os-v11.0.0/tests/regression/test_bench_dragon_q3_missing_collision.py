from tests._v10_helpers import make_case, add_valid_solution, write_json
from mmos.constraints.coverage import constraint_coverage_check
from mmos.certificates.checker import certificate_check


def test_bench_dragon_q3_regression_blocks_0420217_without_collision_validator(tmp_path):
    case = make_case(tmp_path, ('Q2','Q3'))
    add_valid_solution(case, 'Q3', optimal=False, quality='evaluated_best')
    import json
    sol = case/'results/Q3/outputs/solution_real.json'
    obj = json.loads(sol.read_text()); obj['metrics']={'minimal_pitch_m':0.420217}; sol.write_text(json.dumps(obj), encoding='utf-8')
    write_json(case/'workspace/constraints/official/constraint_ledger.json', {'case_id':case.name,'constraints':[{'constraint_id':'Q3_CollisionFreeInheritedFromQ2','question_id':'Q3','constraint_type':'inherited_domain_constraint','description':'Q3 minimal pitch must reuse Q2 collision detector.','depends_on':['Q2_CollisionFreeUntilStop'],'required_solver_hooks':['spiral_motion_generator'],'required_validators':[],'required_negative_tests':['pitch_below_candidate_causes_collision'],'required_certificates':['bracketing_certificate'],'claim_impact':['minimality'],'status':'active'}]})
    assert constraint_coverage_check(case, all_questions=True)['status'] == 'failed'
    assert certificate_check(case, all_questions=True)['status'] == 'failed'
