from __future__ import annotations
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from mmos.quality_oracle.common import registry_questions

DIMENSIONS = {
    'problem_understanding': 10,
    'model_soundness': 15,
    'innovation': 10,
    'solution_quality': 15,
    'validation_strength': 15,
    'robustness': 10,
    'result_interpretability': 8,
    'paper_quality': 10,
    'figure_quality': 5,
    'submission_integrity': 2,
}


def _qid(q: dict[str, Any]) -> str:
    return str(q.get('question_id') or q.get('id') or 'Q?')


def _status_score(report: dict[str, Any], passed: float = 1.0, warning: float = 0.65) -> float:
    s = report.get('status')
    if s in {'passed','ok'}:
        return passed
    if s == 'warning':
        return warning
    return 0.0


def judge_simulate(case_dir: Path, rounds: int = 3, target: str = 'first_prize') -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    out_dir = case_dir / 'reviews' / 'judge_simulation'
    out_dir.mkdir(parents=True, exist_ok=True)
    qs = registry_questions(case_dir)
    qcount = max(len(qs), 1)
    reports = {
        'problem_intelligence': read_json(case_dir / 'quality' / 'problem_intelligence_report.json', {}) or {},
        'modeling': read_json(case_dir / 'quality' / 'modeling_readiness_report.json', {}) or read_json(case_dir / 'quality' / 'modeling_tournament_report.json', {}) or {},
        'solver_benchmark': read_json(case_dir / 'quality' / 'solver_benchmark_report.json', {}) or {},
        'verifier_compare': read_json(case_dir / 'quality' / 'verifier_compare_report.json', {}) or {},
        'paper_quality': read_json(case_dir / 'quality' / 'paper_quality_report.json', {}) or {},
        'figure_plan': read_json(case_dir / 'quality' / 'figure_plan_report.json', {}) or {},
        'output_validate': read_json(case_dir / 'final_outputs' / 'output_validation_report.json', {}) or read_json(case_dir / 'final_outputs' / 'output_validate.json', {}) or {},
    }
    # A generated figures_manifest with existing files is stronger evidence than
    # the initial `figure-plan` scaffold status. Without this normalization,
    # real cases that produced reproducible figures were still scored as 0 in
    # judge simulation because figure-plan reported `planned`.
    fig_manifest = read_json(case_dir / 'paper' / 'figures_manifest.json', {}) or {}
    figures = fig_manifest.get('figures') or []
    if figures:
        complete = all(fig.get('path') and (case_dir / fig.get('path')).exists() and fig.get('source_script') and fig.get('cited_in_section') for fig in figures)
        if complete:
            reports['figure_plan'] = {'status': 'passed', 'figure_count': len(figures), 'source': 'figures_manifest'}
    dim_scores = {
        'problem_understanding': 100 * _status_score(reports['problem_intelligence']),
        'model_soundness': 100 * _status_score(reports['modeling']),
        'innovation': 100 * min(1.0, sum(1 for p in (case_dir/'workspace'/'modeling').glob('*/selected_model.json')) / qcount),
        'solution_quality': 100 * _status_score(reports['solver_benchmark']),
        'validation_strength': 100 * _status_score(reports['verifier_compare']),
        'robustness': 100 * (0.8 if (case_dir/'quality'/'sensitivity_report.json').exists() else 0.4),
        'result_interpretability': 100 * (0.75 if (case_dir/'paper'/'paper_argument_map.json').exists() else 0.35),
        'paper_quality': 100 * _status_score(reports['paper_quality']),
        'figure_quality': 100 * _status_score(reports['figure_plan'], passed=0.75, warning=0.55),
        'submission_integrity': 100 * (1.0 if (case_dir/'registry'/'outputs_registry.json').exists() else 0.2),
    }
    weighted = round(sum(dim_scores[d] * w for d, w in DIMENSIONS.items()) / sum(DIMENSIONS.values()), 2)
    if weighted >= 88:
        grade = 'S'
    elif weighted >= 80:
        grade = 'A'
    elif weighted >= 68:
        grade = 'B'
    elif weighted >= 55:
        grade = 'C'
    else:
        grade = 'D'
    weak = [d for d, s in sorted(dim_scores.items(), key=lambda kv: kv[1]) if s < 75]
    reviewers = {
        'reviewer_A_math': {'focus': 'mathematical rigor', 'score': round((dim_scores['model_soundness'] + dim_scores['validation_strength'] + dim_scores['robustness'])/3, 2)},
        'reviewer_B_engineering': {'focus': 'solver/reproducibility', 'score': round((dim_scores['solution_quality'] + dim_scores['submission_integrity'] + dim_scores['result_interpretability'])/3, 2)},
        'reviewer_C_paper': {'focus': 'paper/figures/exposition', 'score': round((dim_scores['paper_quality'] + dim_scores['figure_quality'] + dim_scores['problem_understanding'])/3, 2)},
    }
    for name, data in reviewers.items():
        write_json(out_dir / f'{name}.json', {'status': 'passed' if data['score'] >= 75 else 'warning', **data, 'generated_at': now_iso()})
    improvements = [{'dimension': d, 'task': f'Improve {d} artifacts and rerun judge-simulate.'} for d in weak[:5]]
    aggregate = {
        'status': 'passed' if weighted >= 80 else ('warning' if weighted >= 60 else 'failed'),
        'target': target,
        'rounds': rounds,
        'score': weighted,
        'grade': grade,
        'dimension_scores': dim_scores,
        'weights': DIMENSIONS,
        'weak_dimensions': weak,
        'reviewers': reviewers,
        'recommended_improvements': improvements,
        'generated_at': now_iso(),
    }
    write_json(out_dir / 'aggregate_review.json', aggregate)
    write_json(out_dir / 'improvement_tasks.json', {'status': 'ok', 'tasks': improvements, 'generated_at': now_iso()})
    write_json(case_dir / 'quality' / 'judge_simulation_report.json', aggregate)
    return aggregate
