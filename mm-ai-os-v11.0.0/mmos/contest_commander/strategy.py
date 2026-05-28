from __future__ import annotations
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from mmos.quality_oracle.common import registry_questions


def _qid(q: dict[str, Any]) -> str:
    return str(q.get('question_id') or q.get('id') or 'Q?')


def build_contest_strategy(case_dir: Path, target: str = 'first_prize', budget: str = 'full', rounds: int = 3) -> dict[str, Any]:
    """Create a first-prize oriented strategy plan.

    This module deliberately produces an executable plan and artifact contract,
    not a fake answer. Agent work remains required for the creative/modeling
    steps, while downstream gates check whether those artifacts were produced.
    """
    case_dir = Path(case_dir).resolve()
    qs = registry_questions(case_dir)
    out_dir = case_dir / 'workspace' / 'contest_strategy'
    out_dir.mkdir(parents=True, exist_ok=True)
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if not qs:
        failures.append({'code': 'NO_REQUIRED_QUESTIONS', 'message': 'Run problem-parse-v2/question-activate before strategy planning.'})

    question_weights = {}
    for i, q in enumerate(qs, start=1):
        qid = _qid(q)
        # Later questions are often synthesis/robustness/output questions. Give
        # them slightly more strategic attention without hard-coding any domain.
        question_weights[qid] = round(1.0 + min(i - 1, 3) * 0.15, 2)

    total_weight = sum(question_weights.values()) or 1.0
    time_budget = []
    for q in qs:
        qid = _qid(q)
        share = question_weights[qid] / total_weight
        time_budget.append({
            'question_id': qid,
            'share': round(share, 3),
            'must_have': ['baseline_model', 'advanced_model', 'solution_real', 'independent_verifier', 'paper_section'],
            'stretch_goal': ['hybrid_model', 'ablation', 'sensitivity_plot', 'judge_simulation_improvement'],
        })

    scoring_hypothesis = {
        'target': target,
        'rubric_assumption': {
            'model_soundness': 0.15,
            'solver_quality': 0.15,
            'validation_strength': 0.15,
            'innovation': 0.10,
            'paper_quality': 0.10,
            'result_interpretability': 0.08,
            'robustness': 0.10,
            'problem_understanding': 0.10,
            'figures': 0.05,
            'submission_integrity': 0.02,
        },
        'cap_rules': [
            'No independent verifier => readiness capped at B.',
            'No advanced model per required question => readiness capped at B.',
            'No paper-quality pass => readiness capped at C.',
            'Any placeholder solver or missing required question => failed.',
        ],
    }
    risk_register = {
        'risks': [
            {'id': 'R1', 'severity': 'P0', 'title': 'Required question missing solution or output', 'mitigation': 'final-gate-check and first-prize-gate-check'},
            {'id': 'R2', 'severity': 'P1', 'title': 'Single weak heuristic presented as strong model', 'mitigation': 'modeling-tournament + solver-benchmark + red-team'},
            {'id': 'R3', 'severity': 'P1', 'title': 'Solver self-verification only', 'mitigation': 'verifier-factory + verifier-compare --strict'},
            {'id': 'R4', 'severity': 'P1', 'title': 'Paper claims unsupported by artifacts', 'mitigation': 'paper-quality-check + report-consistency-check'},
        ],
        'unresolved_p0_p1_count': 4 if qs else 5,
    }
    iteration_log = {
        'rounds_planned': rounds,
        'loop': [
            'baseline coverage',
            'advanced/hybrid modeling',
            'solver/verifier tournament',
            'paper/figure polish',
            'judge simulation',
            'targeted improvement',
        ],
        'entries': [],
    }
    plan = {
        'status': 'failed' if failures else ('warning' if warnings else 'passed'),
        'case_id': case_dir.name,
        'target': target,
        'budget': budget,
        'rounds': rounds,
        'question_count': len(qs),
        'question_weights': question_weights,
        'time_budget': time_budget,
        'first_prize_artifact_contract': [
            'workspace/problem_intelligence/*.json',
            'workspace/modeling/Qx/model_cards/*.md',
            'workspace/modeling/Qx/selected_model.json',
            'results/Qx/solver_runs/*/result.json',
            'results/Qx/independent_verification/verifier_compare.json',
            'paper/paper_outline.json',
            'paper/figures_manifest.json',
            'reviews/judge_simulation/aggregate_review.json',
        ],
        'failures': failures,
        'warnings': warnings,
        'generated_at': now_iso(),
    }
    write_json(out_dir / 'contest_strategy_plan.json', plan)
    write_json(out_dir / 'time_budget_plan.json', {'status': plan['status'], 'time_budget': time_budget, 'generated_at': now_iso()})
    write_json(out_dir / 'scoring_hypothesis.json', scoring_hypothesis)
    write_json(out_dir / 'first_prize_risk_register.json', risk_register)
    write_json(out_dir / 'iteration_log.json', iteration_log)
    md = [
        '# Contest Strategy Plan', '',
        f'- case_id: `{case_dir.name}`',
        f'- target: `{target}`',
        f'- budget: `{budget}`',
        f'- planned rounds: `{rounds}`', '',
        '## Strategic question weights', '',
        '| question | weight | focus |', '|---|---:|---|',
    ]
    for item in time_budget:
        md.append(f"| {item['question_id']} | {question_weights[item['question_id']]} | {', '.join(item['must_have'])} |")
    md.extend(['', '## First-prize cap rules', ''])
    md.extend([f'- {x}' for x in scoring_hypothesis['cap_rules']])
    (out_dir / 'scoring_hypothesis.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    return plan


def improvement_loop(case_dir: Path, rounds: int = 2, target: str = 'first_prize') -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    review = read_json(case_dir / 'reviews' / 'judge_simulation' / 'aggregate_review.json', {}) or {}
    weak = review.get('weak_dimensions') or ['independent_verification_depth', 'paper_quality', 'model_innovation']
    task_dir = case_dir / '.agent' / 'task_cards'
    task_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for r in range(1, rounds + 1):
        path = task_dir / f'improvement_round_{r}.md'
        lines = [
            f'# Improvement Round {r}', '',
            f'- target: `{target}`',
            f'- current simulated grade: `{review.get("grade", "unknown")}`',
            '', '## Weak dimensions to improve', '',
        ]
        lines.extend([f'- {d}' for d in weak])
        lines.extend(['', '## Required actions', '',
                      '- Modify real solver/verifier/paper artifacts; do not only edit this task card.',
                      '- Rerun affected solver, verifier, paper-quality and judge-simulate commands.',
                      '- Add a short evidence note under `quality/improvements/` describing what changed.', ''])
        path.write_text('\n'.join(lines), encoding='utf-8')
        entries.append({'round': r, 'task_card': str(path.relative_to(case_dir)), 'weak_dimensions': weak})
    log_path = case_dir / 'workspace' / 'contest_strategy' / 'iteration_log.json'
    log = read_json(log_path, {'entries': []}) or {'entries': []}
    log.setdefault('entries', []).extend(entries)
    log['status'] = 'planned'
    log['generated_at'] = now_iso()
    write_json(log_path, log)
    report = {'status': 'ok', 'rounds': rounds, 'target': target, 'entries': entries, 'generated_at': now_iso()}
    write_json(case_dir / 'quality' / 'improvement_loop_report.json', report)
    return report
