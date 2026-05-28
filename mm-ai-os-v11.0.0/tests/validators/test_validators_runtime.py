from pathlib import Path
from mmos.validators.runner import validator_build, validator_test
from mmos.validators.negative_tests import negative_test


def test_validator_build_test_and_negative(tmp_path: Path):
    assert validator_build(tmp_path, 'Q1')['status']=='passed'
    assert validator_test(tmp_path, 'Q1')['status']=='passed'
    assert negative_test(tmp_path, 'Q1')['status']=='passed'
