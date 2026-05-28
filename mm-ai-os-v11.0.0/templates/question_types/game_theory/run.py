#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASE_DIR = HERE.parents[2]
QID = HERE.name
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from validate import validate_inputs
from model import build_model
from solve import solve
from report import render_report


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['validate','reduced','real','report'])
    ap.add_argument('--budget', default='regression')
    args = ap.parse_args(argv)

    context = {'case_dir': str(CASE_DIR), 'question_id': QID, 'budget': args.budget}
    out_dir = CASE_DIR / 'results' / QID / 'outputs'
    diag_dir = CASE_DIR / 'results' / QID / 'diagnostics'
    out_dir.mkdir(parents=True, exist_ok=True)
    diag_dir.mkdir(parents=True, exist_ok=True)

    if args.stage == 'validate':
        res = validate_inputs(context)
        write_json(diag_dir / 'validation_result.json', res)
        return 0 if res.get('status') == 'passed' else 2

    model = build_model(context)
    write_json(diag_dir / 'model_spec.json', model)

    if args.stage in {'reduced','real'}:
        res = solve(args.stage, args.budget, context)
        name = 'solution_real.json' if args.stage == 'real' else 'solution_reduced.json'
        write_json(out_dir / name, res)
        return 0 if res.get('status') == 'success' else 3

    if args.stage == 'report':
        result_path = out_dir / 'solution_real.json'
        result = json.loads(result_path.read_text(encoding='utf-8')) if result_path.exists() else solve('report', args.budget, context)
        report = render_report(result)
        report_path = CASE_DIR / 'reports' / f'{QID}_report.md'
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding='utf-8')
        return 0

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
