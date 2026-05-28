from pathlib import Path
from mmos.modeling_os.common import write_json
from mmos.routing.checker import routing_check, routing_promote


def _proposal(case: Path, evidence=True):
    write_json(case/'workspace'/'routing'/'candidate'/'problem_routing_proposal.json', {'case_id':'c','question_id':'Q1','routing_id':'r','candidate_paradigms':[{'paradigm':'simulation','capabilities':['simulation'],'evidence_ids':['ev1'] if evidence else [],'why':'w','required_validators':['v'],'claim_limits':['limit'],'confidence':'high'}],'rejected_paradigms':[{'paradigm':'forecasting','reason':'not asked'}],'requires_human_review':False})


def test_routing_check_and_promote(tmp_path: Path):
    _proposal(tmp_path)
    assert routing_check(tmp_path)['status']=='passed'
    assert routing_promote(tmp_path)['status']=='passed'
    assert (tmp_path/'workspace'/'routing'/'official'/'problem_routing.json').exists()


def test_routing_without_evidence_fails(tmp_path: Path):
    _proposal(tmp_path, evidence=False)
    assert any(f['code']=='ROUTING_PARADIGM_EVIDENCE_MISSING' for f in routing_check(tmp_path)['failures'])
