from tests._v10_helpers import make_case, write_json
from mmos.validator_adequacy.adequacy import validator_adequacy_check


def test_validator_adequacy_blocks_weak_report(tmp_path):
    case = make_case(tmp_path, ('Q1',))
    write_json(case/'results/Q1/reports/validator_report.json', {'validators':[{'validator_id':'v','positive_tests':1,'negative_tests':0,'violations_detected':0}], 'status':'passed'})
    rep = validator_adequacy_check(case, all_questions=True)
    assert rep['status'] == 'failed'
    assert any(f['code'] == 'VALIDATOR_NO_NEGATIVE_DETECTION' for f in rep['failures'])


def test_validator_adequacy_passes_with_detection(tmp_path):
    case = make_case(tmp_path, ('Q1',))
    write_json(case/'results/Q1/reports/validator_report.json', {'validators':[{'validator_id':'v','positive_tests':1,'negative_tests':1,'violations_detected':1,'mutation_detected':True}], 'status':'passed'})
    assert validator_adequacy_check(case, all_questions=True)['status'] == 'passed'
