from pathlib import Path
import json


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')


def make_case(tmp_path: Path, qids=("Q1",)) -> Path:
    case = tmp_path / 'case_x'
    (case / 'registry').mkdir(parents=True)
    write_json(case / 'registry' / 'questions_registry.json', {'questions':[{'question_id':q, 'required':True} for q in qids]})
    return case


def add_valid_solution(case: Path, qid='Q1', *, optimal=False, quality='evaluated_best'):
    art = case / 'results' / qid / 'outputs' / 'artifact.txt'
    art.parent.mkdir(parents=True, exist_ok=True)
    art.write_text('ok', encoding='utf-8')
    write_json(case / 'results' / qid / 'outputs' / 'solution_real.json', {
        'question_id': qid,
        'scope': 'real',
        'data_source': 'problem_statement_derived',
        'experiment_id': f'{qid}_exp',
        'model': 'deterministic_model',
        'method': 'deterministic_solver',
        'quality_level': quality,
        'solver_status': 'completed',
        'optimal': optimal,
        'metrics': {'value': 1.0},
        'violation_count': 0,
        'diagnostics': {'constraints_checked': True, 'domain_validators_run': ['unit_check'], 'fallback_used': False},
        'artifacts': [f'results/{qid}/outputs/artifact.txt'],
        'limitations': 'Deterministic fixture for gate tests.'
    })


def add_validator(case: Path, qid='Q1'):
    qdir = case / 'engineering' / 'questions' / qid
    (qdir / 'tests' / 'positive').mkdir(parents=True, exist_ok=True)
    (qdir / 'tests' / 'negative').mkdir(parents=True, exist_ok=True)
    (qdir / 'validators.py').write_text('''\ndef validate(data):\n    failures=[]\n    if data.get("value", 0) > 10:\n        failures.append({"code":"TOO_LARGE"})\n    if "value" not in data:\n        failures.append({"code":"MISSING_VALUE"})\n    return {"status":"failed" if failures else "passed", "failures": failures, "violation_count": len(failures)}\n''', encoding='utf-8')
    write_json(qdir / 'tests' / 'positive' / 'ok.json', {'value': 1})
    write_json(qdir / 'tests' / 'negative' / 'bad.json', {'value': 99})
