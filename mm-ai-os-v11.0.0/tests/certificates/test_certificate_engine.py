from tests._v10_helpers import make_case, add_valid_solution, write_json
from mmos.certificates.checker import certificate_check


def test_missing_certificate_blocks_minimal_claim(tmp_path):
    case = make_case(tmp_path, ('Q3',))
    add_valid_solution(case, 'Q3', optimal=False, quality='evaluated_best')
    # A keyword in metrics/solution triggers certificate requirement.
    sol = case/'results/Q3/outputs/solution_real.json'
    import json
    obj = json.loads(sol.read_text())
    obj['metrics'] = {'minimal_pitch_m': 0.42}
    sol.write_text(json.dumps(obj), encoding='utf-8')
    rep = certificate_check(case, all_questions=True)
    assert rep['status'] == 'failed'
    assert any(f['code'] == 'MISSING_CERTIFICATE' for f in rep['failures'])


def test_certificate_check_passes_bracketing_certificate(tmp_path):
    case = make_case(tmp_path, ('Q3',))
    add_valid_solution(case, 'Q3', optimal=False, quality='evaluated_best')
    import json
    sol = case/'results/Q3/outputs/solution_real.json'
    obj = json.loads(sol.read_text()); obj['metrics']={'minimal_pitch_m':0.450338}; sol.write_text(json.dumps(obj), encoding='utf-8')
    write_json(case/'results/Q3/reports/optimization_certificate.json', {
        'certificate_id':'Q3_min_pitch', 'question_id':'Q3', 'certificate_type':'bracketing_certificate',
        'target':'minimal_pitch_m', 'candidate_value':0.450338, 'lower_bound':0.450337, 'upper_bound':0.450339,
        'feasibility_check': {'status':'feasible','validators':['collision_free_until_turning_boundary']},
        'infeasibility_check': {'status':'infeasible','violated_constraints':['collision_free_until_turning_boundary']},
        'counterexample_probe': {'type':'p_minus_epsilon','status':'failed_as_expected'},
        'certificate_status':'pass'
    })
    assert certificate_check(case, all_questions=True)['status'] == 'passed'
