from __future__ import annotations
from pathlib import Path
from mmos.modeling_os.common import read_jsonl, write_json, status_from, resolve_case_file


def claim_check(case_dir: Path, all_claims: bool = True) -> dict:
    case_dir=Path(case_dir).resolve()
    claims=read_jsonl(case_dir/'reports'/'evidence_claims.jsonl')
    final_claims=read_jsonl(case_dir/'reports'/'final_claims.jsonl')
    failures=[]; warnings=[]
    if not claims:
        failures.append({'code':'NO_CLAIMS','message':'reports/evidence_claims.jsonl is missing or empty.'})
    for c in claims:
        cid=c.get('claim_id')
        if not c.get('experiment_id'):
            failures.append({'code':'CLAIM_MISSING_EXPERIMENT_ID','claim_id':cid})
        if not c.get('source_artifact'):
            failures.append({'code':'CLAIM_MISSING_SOURCE_ARTIFACT','claim_id':cid})
        elif not resolve_case_file(case_dir, c['source_artifact']).exists():
            failures.append({'code':'CLAIM_SOURCE_ARTIFACT_MISSING','claim_id':cid,'source_artifact':c.get('source_artifact')})
        if c.get('confidence') == 'high' and len(c.get('validators') or []) < 2:
            failures.append({'code':'HIGH_CONFIDENCE_VALIDATOR_INSUFFICIENT','claim_id':cid})
        if not c.get('limitations'):
            failures.append({'code':'CLAIM_LIMITATIONS_MISSING','claim_id':cid})
    for c in final_claims:
        if c.get('confidence') == 'low' and c.get('allowed_in_abstract'):
            failures.append({'code':'LOW_CONFIDENCE_ABSTRACT_BLOCKED','claim_id':c.get('claim_id')})
        if not c.get('experiment_id'):
            failures.append({'code':'FINAL_CLAIM_MISSING_EXPERIMENT_ID','claim_id':c.get('claim_id')})
        if not c.get('source_artifact'):
            failures.append({'code':'FINAL_CLAIM_MISSING_SOURCE_ARTIFACT','claim_id':c.get('claim_id')})
    report={'status':status_from(failures,warnings),'claim_count':len(claims),'final_claim_count':len(final_claims),'failures':failures,'warnings':warnings}
    write_json(case_dir/'reports'/'claim_check_report.json', report)
    return report
