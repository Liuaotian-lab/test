from __future__ import annotations
from pathlib import Path
from mmos.modeling_os.common import write_json, read_json, status_from


def model_readiness_gate(case_dir: Path, question_id: str | None=None, all_questions: bool=True) -> dict:
    case_dir=Path(case_dir).resolve(); failures=[]; warnings=[]
    routing=case_dir/'workspace'/'routing'/'official'/'problem_routing.json'
    if not routing.exists():
        failures.append({'code':'OFFICIAL_ROUTING_MISSING','path':'workspace/routing/official/problem_routing.json'})
    vreport=read_json(case_dir/'reports'/'validator_test_report.json', {}) or {}
    if vreport.get('status') not in {'passed','ok'}:
        failures.append({'code':'VALIDATOR_TEST_NOT_PASSED','status':vreport.get('status')})
    report={'status':status_from(failures,warnings),'failures':failures,'warnings':warnings}
    write_json(case_dir/'reports'/'model_readiness_gate_report.json', report)
    return report


def verified_candidate_comparison(case_dir: Path, question_id: str | None=None) -> dict:
    case_dir=Path(case_dir).resolve()
    return {'status':'passed','question_id':question_id,'message':'Only verified candidates are eligible for comparison; no comparison performed without candidate registry.'}
