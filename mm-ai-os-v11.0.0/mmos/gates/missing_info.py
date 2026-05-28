from __future__ import annotations
from pathlib import Path
from mmos.kernel.jsonio import read_json, write_json


def missing_info_check(case_dir: Path, question_id: str | None = None) -> dict:
    case_dir = Path(case_dir).resolve()
    qdirs = [case_dir / 'contracts' / 'questions' / question_id] if question_id else sorted((case_dir / 'contracts' / 'questions').glob('Q*'))
    failures=[]; warnings=[]
    for qdir in qdirs:
        qid = qdir.name
        data = read_json(qdir / 'missing_information_contract.json', default=None)
        if data is None:
            failures.append({'code': 'MISSING_MISSING_INFO_CONTRACT', 'question_id': qid})
            continue
        items = data.get('missing_items', []) or []
        disclosure_required = bool(data.get('disclosure_required') or any(i.get('impact') for i in items))
        if disclosure_required and not items:
            warnings.append({'code': 'DISCLOSURE_REQUIRED_BUT_NO_ITEMS', 'question_id': qid})
        for item in items:
            if item.get('required_for') and not item.get('assumption_used') and data.get('allowed_to_output_numeric_answer', True):
                warnings.append({'code': 'MISSING_ASSUMPTION_FOR_NUMERIC_OUTPUT', 'question_id': qid, 'item': item.get('item')})
    report={'gate':'missing-info-check','question_id':question_id,'status':'failed' if failures else ('warning' if warnings else 'passed'),'failures':failures,'warnings':warnings}
    write_json(case_dir / '.agent' / 'gate_reports' / (f'{question_id}_missing_info_check.json' if question_id else 'case_missing_info_check.json'), report)
    return report
