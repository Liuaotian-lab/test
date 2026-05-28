from pathlib import Path
import json
from mmos.modeling_os.common import append_jsonl
from mmos.evidence.claims import evidence_pack_case
from mmos.evidence.claim_check import claim_check


def test_evidence_pack_and_claim_check(tmp_path: Path):
    src=tmp_path/'results'/'Q1'/'outputs'/'solution_real.json'; src.parent.mkdir(parents=True); src.write_text('{}', encoding='utf-8')
    append_jsonl(tmp_path/'reports'/'experiments_summary.jsonl', [{'experiment_id':'E1','question_id':'Q1','model':'m','method':'method','quality_level':'simulation_estimate','solver_status':'completed','scope':'real','data_source':'problem_statement_derived','metrics':{'x':1},'conclusion':'Q1 generated output.','limitations':'No optimization claim.','artifacts':['results/Q1/outputs/solution_real.json'],'validators':['solver_verify','domain_validate'],'violation_count':0,'created_at':'now','source_solution':'results/Q1/outputs/solution_real.json'}])
    assert evidence_pack_case(tmp_path)['status']=='passed'
    assert claim_check(tmp_path)['status']=='passed'


def test_claim_missing_experiment_id_fails(tmp_path: Path):
    src=tmp_path/'a.json'; src.write_text('{}', encoding='utf-8')
    append_jsonl(tmp_path/'reports'/'evidence_claims.jsonl', [{'claim_id':'c','question_id':'Q1','claim':'x','experiment_id':'','source_artifact':'a.json','confidence':'high','validators':['a','b'],'limitations':'l','allowed_in_paper':True,'allowed_in_abstract':True}])
    assert any(f['code']=='CLAIM_MISSING_EXPERIMENT_ID' for f in claim_check(tmp_path)['failures'])


def test_claim_missing_artifact_fails(tmp_path: Path):
    append_jsonl(tmp_path/'reports'/'evidence_claims.jsonl', [{'claim_id':'c','question_id':'Q1','claim':'x','experiment_id':'e','source_artifact':'missing.json','confidence':'high','validators':['a','b'],'limitations':'l','allowed_in_paper':True,'allowed_in_abstract':True}])
    assert any(f['code']=='CLAIM_SOURCE_ARTIFACT_MISSING' for f in claim_check(tmp_path)['failures'])


def test_low_confidence_abstract_fails(tmp_path: Path):
    src=tmp_path/'a.json'; src.write_text('{}', encoding='utf-8')
    append_jsonl(tmp_path/'reports'/'evidence_claims.jsonl', [{'claim_id':'c','question_id':'Q1','claim':'x','experiment_id':'e','source_artifact':'a.json','confidence':'low','validators':['a','b'],'limitations':'l','allowed_in_paper':False,'allowed_in_abstract':False}])
    append_jsonl(tmp_path/'reports'/'final_claims.jsonl', [{'claim_id':'c','question_id':'Q1','claim':'x','experiment_id':'e','source_artifact':'a.json','confidence':'low','allowed_in_paper':True,'allowed_in_abstract':True}])
    assert any(f['code']=='LOW_CONFIDENCE_ABSTRACT_BLOCKED' for f in claim_check(tmp_path)['failures'])
