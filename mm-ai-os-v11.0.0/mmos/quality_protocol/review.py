from __future__ import annotations
from pathlib import Path
from mmos.modeling_os.common import write_json, read_json, status_from


def _issue(issue_id, severity, issue_type, message, evidence, action, question_id=None):
    d={'issue_id':issue_id,'severity':severity,'issue_type':issue_type,'message':message,'evidence':evidence,'required_action':action}
    if question_id: d['question_id']=question_id
    return d


def quality_review(case_dir: Path, all_questions: bool=True) -> dict:
    case_dir=Path(case_dir).resolve(); issues=[]
    for report in sorted((case_dir/'reports').glob('*_report.json')) if (case_dir/'reports').exists() else []:
        data=read_json(report,{}) or {}
        if data.get('status')=='failed':
            issues.append(_issue(f'issue_{len(issues)+1:03d}','warning','failed_report',f'{report.name} has failed status.',[str(report.relative_to(case_dir))],'Inspect and repair failed report.'))
    blocking=[i for i in issues if i['severity']=='blocking']
    out={'status':status_from(blocking, issues if not blocking else []),'issues':issues,'blocking_issue_count':len(blocking)}
    write_json(case_dir/'reports'/'quality_review_report.json', out)
    return out
