from tests._v10_helpers import make_case
from mmos.agent_protocol.runtime import task_card_build, failure_ledger_add, repair_check


def test_task_card_and_failure_ledger(tmp_path):
    case = make_case(tmp_path, ('Q1',))
    assert task_card_build(case, role='solver_engineer', question_id='Q1')['status'] == 'passed'
    assert failure_ledger_add(case, command='bad command', root_cause='fixture')['status'] == 'passed'
    assert repair_check(case)['status'] == 'passed'
