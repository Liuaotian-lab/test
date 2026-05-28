from __future__ import annotations
from pathlib import Path
from typing import Any
import csv
from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from mmos.quality_oracle.common import registry_questions, read_solution

SOLVER_KINDS = ['baseline', 'advanced', 'hybrid', 'ablation']


def _qid(q: dict[str, Any]) -> str:
    return str(q.get('question_id') or q.get('id') or 'Q?')


def solver_factory(case_dir: Path, question_id: str | None = None, force: bool = False) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    created=[]; warnings=[]; failures=[]
    qs = [q for q in registry_questions(case_dir) if not question_id or _qid(q) == question_id]
    if not qs:
        failures.append({'code': 'NO_REQUIRED_QUESTIONS'})
    for q in qs:
        qid = _qid(q)
        sdir = case_dir / 'engineering' / 'questions' / qid / 'solvers'
        sdir.mkdir(parents=True, exist_ok=True)
        selected = read_json(case_dir / 'workspace' / 'modeling' / qid / 'selected_model.json', {}) or {}
        for kind in SOLVER_KINDS:
            path = sdir / f'{kind}_solver_spec.md'
            if force or not path.exists():
                path.write_text(f"""# {qid} {kind.title()} Solver Spec

- question_id: `{qid}`
- solver_kind: `{kind}`
- selected_model: `{(selected.get('selected_model') or {}).get('model_id', 'unknown')}`

## Required implementation
Agent must implement or bind a real executable solver variant. Do not submit this spec as a solver result.

## Required output
Write a benchmark artifact to:

`results/{qid}/solver_runs/{kind}/result.json`

with fields:

```json
{{
  "question_id": "{qid}",
  "solver_kind": "{kind}",
  "status": "success",
  "objective_value": 0.0,
  "feasible": true,
  "robustness_score": 0.0,
  "runtime_seconds": 0.0,
  "explainability_score": 0.0,
  "verification_score": 0.0,
  "risk_score": 0.0
}}
```
""", encoding='utf-8')
            created.append(str(path.relative_to(case_dir)))
        (case_dir / 'results' / qid / 'solver_runs').mkdir(parents=True, exist_ok=True)
    report = {'status': 'failed' if failures else 'ok', 'created': created, 'warnings': warnings, 'failures': failures, 'generated_at': now_iso()}
    write_json(case_dir / 'quality' / 'solver_factory_report.json', report)
    return report


def _score_result(result: dict[str, Any]) -> float:
    feasible = 1.0 if result.get('feasible', True) is not False else 0.0
    robustness = float(result.get('robustness_score', result.get('robustness', 0.5)) or 0.0)
    explain = float(result.get('explainability_score', result.get('explainability', 0.5)) or 0.0)
    verify = float(result.get('verification_score', result.get('verification', 0.5)) or 0.0)
    risk = float(result.get('risk_score', result.get('risk', 0.3)) or 0.0)
    runtime = float(result.get('runtime_seconds', 1.0) or 1.0)
    runtime_score = max(0.0, min(1.0, 1.0 / max(runtime, 1.0)))
    return round(100 * (0.25*feasible + 0.20*robustness + 0.20*verify + 0.15*explain + 0.10*runtime_score + 0.10*(1.0-risk)), 2)


def solver_benchmark(case_dir: Path, question_id: str | None = None, strict: bool = False, min_variants: int = 2) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    failures=[]; warnings=[]; summaries=[]
    qs = [q for q in registry_questions(case_dir) if not question_id or _qid(q) == question_id]
    if not qs:
        failures.append({'code': 'NO_REQUIRED_QUESTIONS'})
    for q in qs:
        qid = _qid(q)
        runs_dir = case_dir / 'results' / qid / 'solver_runs'
        results=[]
        if runs_dir.exists():
            for p in sorted(runs_dir.glob('*/result.json')):
                data = read_json(p, {}) or {}
                data['path'] = str(p.relative_to(case_dir))
                data['computed_score'] = _score_result(data)
                results.append(data)
        if not results:
            sol = read_solution(case_dir, qid)
            if sol:
                # Main solution can seed a single benchmark entry, but strict first-prize
                # readiness still requires multiple independent variants.
                seeded = {
                    'question_id': qid,
                    'solver_kind': 'main_solution_seed',
                    'status': sol.get('status'),
                    'objective_value': sol.get('objective_value'),
                    'feasible': (sol.get('diagnostics') or {}).get('constraints_checked') is True,
                    'robustness_score': 0.45,
                    'explainability_score': 0.5,
                    'verification_score': 0.4,
                    'risk_score': 0.5,
                    'runtime_seconds': 1.0,
                    'path': f'results/{qid}/outputs/solution_real.json',
                }
                seeded['computed_score'] = _score_result(seeded)
                results.append(seeded)
                warnings.append({'code': 'ONLY_MAIN_SOLUTION_SEEDED_BENCHMARK', 'question_id': qid})
        if len(results) < min_variants:
            (failures if strict else warnings).append({'code': 'INSUFFICIENT_SOLVER_VARIANTS', 'question_id': qid, 'count': len(results), 'minimum': min_variants})
        results = sorted(results, key=lambda x: x.get('computed_score', 0), reverse=True)
        best = results[0] if results else None
        summary = {'question_id': qid, 'variant_count': len(results), 'best': best, 'results': results}
        summaries.append(summary)
        qout = case_dir / 'results' / qid / 'solver_runs'
        qout.mkdir(parents=True, exist_ok=True)
        write_json(qout / 'benchmark_report.json', summary)
        with (qout / 'benchmark_scoreboard.csv').open('w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['solver_kind','computed_score','feasible','robustness','verification','explainability','risk','path'])
            for r in results:
                writer.writerow([r.get('solver_kind'), r.get('computed_score'), r.get('feasible'), r.get('robustness_score'), r.get('verification_score'), r.get('explainability_score'), r.get('risk_score'), r.get('path')])
    status = 'failed' if failures else ('warning' if warnings else 'passed')
    report = {'gate': 'solver-benchmark', 'status': status, 'strict': strict, 'min_variants': min_variants, 'summaries': summaries, 'failures': failures, 'warnings': warnings, 'generated_at': now_iso()}
    write_json(case_dir / 'quality' / 'solver_benchmark_report.json', report)
    return report
