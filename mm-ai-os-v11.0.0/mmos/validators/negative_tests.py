from __future__ import annotations
from pathlib import Path
from .runner import validator_test
from mmos.modeling_os.common import write_json


def negative_test(case_dir: Path, question_id: str | None = None) -> dict:
    report=validator_test(case_dir, question_id=question_id)
    negative=[]
    for q in report.get('questions',[]):
        negative.append({'question_id':q.get('question_id'),'negative_tests':q.get('negative_tests',0),'violations_detected':q.get('violations_detected',0),'status':'passed' if q.get('violations_detected',0) > 0 else 'failed'})
    failures=[]
    for n in negative:
        if n['status']!='passed':
            failures.append({'code':'NEGATIVE_TEST_COVERAGE_FAILED','question_id':n.get('question_id')})
    out={'status':'failed' if failures or report.get('status')=='failed' else 'passed','negative_tests':negative,'failures':failures + report.get('failures',[])}
    write_json(Path(case_dir)/'reports'/'negative_test_report.json', out)
    return out
