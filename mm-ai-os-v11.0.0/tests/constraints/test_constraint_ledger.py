from tests._v10_helpers import make_case, write_json
from mmos.constraints.ledger import check_constraint_ledger
from mmos.constraints.coverage import constraint_coverage_check


def test_constraint_coverage_blocks_missing_inherited_validator(tmp_path):
    case = make_case(tmp_path, ('Q2','Q3'))
    write_json(case/'workspace/constraints/official/constraint_ledger.json', {
        'case_id': case.name,
        'constraints': [{
            'constraint_id': 'Q3_CollisionFreeInheritedFromQ2',
            'question_id': 'Q3',
            'constraint_type': 'inherited_domain_constraint',
            'description': 'Q3 must inherit Q2 collision-free condition.',
            'depends_on': ['Q2_CollisionFreeUntilStop'],
            'required_solver_hooks': ['spiral_solver'],
            'required_validators': [],
            'required_negative_tests': ['pitch_below_candidate_causes_collision'],
            'required_certificates': ['bracketing_certificate'],
            'claim_impact': ['minimality'],
            'status': 'active'
        }]
    })
    report = constraint_coverage_check(case, all_questions=True)
    assert report['status'] == 'failed'
    assert any(f['code'] == 'MISSING_VALIDATOR' for f in report['failures'])


def test_constraint_coverage_passes_complete_constraint(tmp_path):
    case = make_case(tmp_path, ('Q1',))
    write_json(case/'workspace/constraints/official/constraint_ledger.json', {
        'case_id': case.name,
        'constraints': [{
            'constraint_id': 'Q1_OUT_001', 'question_id': 'Q1', 'constraint_type': 'output_format',
            'description': 'Output must exist.', 'depends_on': [],
            'required_solver_hooks': ['output_builder'], 'required_validators': ['output_template_check'],
            'required_negative_tests': ['missing_required_output'], 'required_certificates': [],
            'claim_impact': ['output'], 'status': 'active'}]
    })
    assert check_constraint_ledger(case)['status'] == 'passed'
    assert constraint_coverage_check(case)['status'] == 'passed'
