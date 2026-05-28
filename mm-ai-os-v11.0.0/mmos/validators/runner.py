from __future__ import annotations
from pathlib import Path
import importlib.util, json
from mmos.modeling_os.common import write_json, status_from, question_ids, read_json
from .base import normalize_validation_result


def _question_dir(case_dir: Path, qid: str) -> Path:
    for base in [case_dir/'engineering'/'questions', case_dir/'questions']:
        q=base/qid
        if q.exists():
            return q
    return case_dir/'engineering'/'questions'/qid


def _load_validator(path: Path):
    spec=importlib.util.spec_from_file_location(f'_mmos_validator_{hash(path)}', path)
    mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    if hasattr(mod, 'validate'):
        return mod.validate
    funcs=[getattr(mod, n) for n in dir(mod) if n.startswith('validate_') and callable(getattr(mod,n))]
    if not funcs:
        return None
    def combined(data):
        failures=[]
        for fn in funcs:
            res=normalize_validation_result(fn(data))
            failures.extend(res.get('failures') or [])
        return {'status':'failed' if failures else 'passed','failures':failures,'violation_count':len(failures)}
    return combined


def validator_test(case_dir: Path, question_id: str | None = None) -> dict:
    case_dir=Path(case_dir).resolve(); failures=[]; warnings=[]; qreports=[]
    ids=[question_id] if question_id else question_ids(case_dir)
    if not ids:
        failures.append({'code':'NO_QUESTIONS_FOR_VALIDATOR_TEST'})
    for qid in ids:
        qdir=_question_dir(case_dir, qid)
        issues=[]; pos_count=0; neg_count=0; detected=0
        vpath=qdir/'validators.py'
        if not vpath.exists():
            issues.append({'code':'VALIDATORS_PY_MISSING','question_id':qid})
        fn=None
        if vpath.exists():
            text=vpath.read_text(encoding='utf-8', errors='replace')
            if 'return True' in text:
                issues.append({'code':'EMPTY_OR_TRIVIAL_VALIDATOR','question_id':qid})
            try:
                fn=_load_validator(vpath)
            except Exception as exc:
                issues.append({'code':'VALIDATOR_IMPORT_FAILED','question_id':qid,'message':str(exc)})
            if fn is None:
                issues.append({'code':'VALIDATOR_FUNCTION_MISSING','question_id':qid})
        for kind in ['positive','negative']:
            tdir=qdir/'tests'/kind
            files=sorted(tdir.glob('*.json')) if tdir.exists() else []
            if kind=='positive': pos_count=len(files)
            else: neg_count=len(files)
            if not files:
                issues.append({'code':f'{kind.upper()}_TESTS_MISSING','question_id':qid})
            if fn:
                for fixture in files:
                    data=read_json(fixture, {}) or {}
                    res=normalize_validation_result(fn(data))
                    if kind=='positive' and res['status']!='passed':
                        issues.append({'code':'POSITIVE_TEST_FAILED','question_id':qid,'fixture':fixture.name,'result':res})
                    if kind=='negative' and res.get('violation_count',0)<=0:
                        issues.append({'code':'NEGATIVE_TEST_NOT_DETECTED','question_id':qid,'fixture':fixture.name})
                    if kind=='negative' and res.get('violation_count',0)>0:
                        detected+=1
        qreport={'question_id':qid,'validators':[{'validator_id':'validate','status':'failed' if issues else 'pass','positive_tests':pos_count,'negative_tests':neg_count,'violations_detected':detected,'blocking_issues':issues}], 'status':'failed' if issues else 'passed', 'positive_tests':pos_count,'negative_tests':neg_count,'violations_detected':detected,'blocking_issues':issues}
        qreports.append(qreport)
        failures.extend(issues)
        write_json(case_dir/'engineering'/'results'/qid/'reports'/'validator_report.json', qreport)
    report={'status':status_from(failures,warnings),'questions':qreports,'failures':failures,'warnings':warnings}
    write_json(case_dir/'reports'/'validator_test_report.json', report)
    return report


def validator_build(case_dir: Path, question_id: str) -> dict:
    case_dir=Path(case_dir).resolve(); qdir=case_dir/'engineering'/'questions'/question_id
    (qdir/'tests'/'positive').mkdir(parents=True, exist_ok=True); (qdir/'tests'/'negative').mkdir(parents=True, exist_ok=True)
    (qdir/'constraints.py').write_text('REQUIRED_KEY = "value"\nMAX_VALUE = 10\n', encoding='utf-8')
    (qdir/'validators.py').write_text('def validate(data):\n    failures=[]\n    if "value" not in data:\n        failures.append({"code":"MISSING_REQUIRED_OUTPUT"})\n    elif data.get("value") > 10:\n        failures.append({"code":"WRONG_CONSTRAINT"})\n    return {"status":"failed" if failures else "passed", "failures":failures, "violation_count":len(failures)}\n', encoding='utf-8')
    (qdir/'tests'/'positive'/'ok.json').write_text(json.dumps({'value':1}), encoding='utf-8')
    (qdir/'tests'/'negative'/'wrong_constraint.json').write_text(json.dumps({'value':99}), encoding='utf-8')
    plan={'question_id':question_id,'validators':['validate'],'positive_fixtures':['ok.json'],'negative_fixtures':['wrong_constraint.json']}
    write_json(qdir/'validator_test_plan.json', plan)
    return {'status':'passed','question_id':question_id,'outputs':[str((qdir/'validators.py').relative_to(case_dir)),str((qdir/'validator_test_plan.json').relative_to(case_dir))]}
