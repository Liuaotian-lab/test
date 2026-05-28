from __future__ import annotations
from pathlib import Path
from typing import Any
import csv
from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from mmos.quality_oracle.common import registry_questions

LEVELS = [
    ('L0', 'naive_baseline', 45, '可快速验证题意与输出格式的朴素基线。'),
    ('L1', 'contest_baseline', 62, '常规竞赛可接受模型，变量/目标/约束明确。'),
    ('L2', 'advanced_competition_model', 78, '加入对照、约束复核、稳健性或领域结构的高级模型。'),
    ('L3', 'innovation_or_hybrid_model', 86, '融合领域机制、优化/预测/仿真组合和可解释验证的冲奖模型。'),
]


def _qid(q: dict[str, Any]) -> str:
    return str(q.get('question_id') or q.get('id') or 'Q?')


def _model_card(case_id: str, q: dict[str, Any], level: str, model_id: str, base_score: int, desc: str) -> str:
    qid = _qid(q)
    title = q.get('title') or q.get('source_excerpt', '')[:120]
    return f"""# {qid} {model_id} Model Card

- case_id: `{case_id}`
- question_id: `{qid}`
- title: {title}
- level: `{level}`
- expected_strength_score: `{base_score}`

## Purpose
{desc}

## Variables
- Agent must refine decision/state/random variables in `contracts/questions/{qid}/variable_registry.json`.

## Objective
- Agent must bind the objective/metric to `objective_registry.json` and `solution_real.json`.

## Constraints
- Agent must list hard constraints, soft constraints, and feasibility checks.

## Data inputs
- `data/raw/*`
- `data/manifest/data_manifest.json`

## Verification plan
- Baseline comparison
- Constraint recomputation
- Independent metric recomputation
- Sensitivity/robustness checks

## Paper value
- Explain why this model is stronger than the previous level.
- Provide at least one figure/table opportunity.

## Failure modes
- Hidden unit mismatch
- Unsupported optimality claim
- Data leakage or overfitting if prediction is involved
- Overly optimistic heuristic result without verifier
"""


def modeling_tournament(case_dir: Path, question_id: str | None = None, target: str = 'first_prize') -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    qs = [q for q in registry_questions(case_dir) if not question_id or _qid(q) == question_id]
    failures=[]; warnings=[]; summaries=[]
    if not qs:
        failures.append({'code': 'NO_REQUIRED_QUESTIONS'})
    for q in qs:
        qid = _qid(q)
        qdir = case_dir / 'workspace' / 'modeling' / qid
        cards_dir = qdir / 'model_cards'
        cards_dir.mkdir(parents=True, exist_ok=True)
        candidates=[]
        rows=[]
        for level, model_id, base_score, desc in LEVELS:
            card_path = cards_dir / f'{model_id}.md'
            if not card_path.exists():
                card_path.write_text(_model_card(case_dir.name, q, level, model_id, base_score, desc), encoding='utf-8')
            scores = {
                'correctness': min(95, base_score + 2),
                'constraint_completeness': min(95, base_score),
                'innovation': min(98, base_score + (12 if level == 'L3' else 4)),
                'feasibility': max(35, 90 - (10 if level == 'L3' else 0)),
                'verifiability': min(92, base_score + 3),
                'paper_value': min(95, base_score + (8 if level in {'L2','L3'} else 0)),
            }
            weighted = round(0.25*scores['correctness'] + 0.15*scores['constraint_completeness'] + 0.15*scores['innovation'] + 0.15*scores['feasibility'] + 0.15*scores['verifiability'] + 0.15*scores['paper_value'], 2)
            cand = {
                'model_id': model_id,
                'level': level,
                'description': desc,
                'card': str(card_path.relative_to(case_dir)),
                'scores': scores,
                'weighted_score': weighted,
                'required_agent_action': 'Replace generic card fields with domain-specific variables/objectives/constraints before first-prize gate.',
            }
            candidates.append(cand)
            rows.append([model_id, level, weighted, scores['correctness'], scores['innovation'], scores['verifiability'], scores['paper_value']])
        selected = max(candidates, key=lambda x: x['weighted_score']) if candidates else None
        write_json(qdir / 'model_idea_pool.json', {'status': 'passed', 'question_id': qid, 'target': target, 'candidates': candidates, 'generated_at': now_iso()})
        write_json(qdir / 'selected_model.json', {'status': 'passed', 'question_id': qid, 'selected_model': selected, 'selection_reason': 'Highest weighted first-prize readiness score; Agent must refine and implement.', 'generated_at': now_iso()})
        with (qdir / 'model_selection_matrix.csv').open('w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['model_id','level','weighted_score','correctness','innovation','verifiability','paper_value'])
            writer.writerows(rows)
        md = ['# Model Selection Report', '', f'- question_id: `{qid}`', f'- target: `{target}`', '', '| model | level | score | card |', '|---|---|---:|---|']
        for c in candidates:
            md.append(f"| {c['model_id']} | {c['level']} | {c['weighted_score']} | `{c['card']}` |")
        if selected:
            md.extend(['', '## Selected model', '', f"`{selected['model_id']}` / `{selected['level']}`. Agent must implement this in solver/verifier artifacts."])
        (qdir / 'model_selection.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
        (case_dir / 'reports').mkdir(exist_ok=True)
        (case_dir / 'reports' / f'{qid}_model_selection.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
        contract_path = case_dir / 'contracts' / 'questions' / qid / 'model_candidates.json'
        if contract_path.parent.exists():
            write_json(contract_path, {'status': 'refined', 'question_id': qid, 'candidates': candidates, 'selected_model_id': selected['model_id'] if selected else None})
        summaries.append({'question_id': qid, 'candidate_count': len(candidates), 'selected_model': selected})
    status = 'failed' if failures else ('warning' if warnings else 'passed')
    report = {'gate': 'modeling-tournament', 'status': status, 'target': target, 'summaries': summaries, 'failures': failures, 'warnings': warnings, 'generated_at': now_iso()}
    write_json(case_dir / 'quality' / 'modeling_tournament_report.json', report)
    return report


def modeling_readiness_check(case_dir: Path, question_id: str | None = None, strict: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    failures=[]; warnings=[]; evidence=[]
    qs = [q for q in registry_questions(case_dir) if not question_id or _qid(q) == question_id]
    if not qs:
        failures.append({'code': 'NO_REQUIRED_QUESTIONS'})
    for q in qs:
        qid = _qid(q)
        pool = read_json(case_dir / 'workspace' / 'modeling' / qid / 'model_idea_pool.json', {}) or {}
        selected = read_json(case_dir / 'workspace' / 'modeling' / qid / 'selected_model.json', {}) or {}
        candidates = pool.get('candidates') or []
        levels = {c.get('level') for c in candidates}
        item = {'question_id': qid, 'candidate_count': len(candidates), 'levels': sorted(x for x in levels if x), 'selected_model_exists': bool(selected.get('selected_model'))}
        evidence.append(item)
        if len(candidates) < 3:
            failures.append({'code': 'INSUFFICIENT_MODEL_CANDIDATES', 'question_id': qid, 'count': len(candidates), 'minimum': 3})
        if 'L0' not in levels:
            failures.append({'code': 'MISSING_BASELINE_MODEL', 'question_id': qid})
        if not ({'L2','L3'} & levels):
            failures.append({'code': 'MISSING_ADVANCED_MODEL', 'question_id': qid})
        if not selected.get('selected_model'):
            failures.append({'code': 'MISSING_SELECTED_MODEL', 'question_id': qid})
        # Generic cards are acceptable as a scaffold, but not for strict first-prize readiness.
        if strict:
            cards = list((case_dir / 'workspace' / 'modeling' / qid / 'model_cards').glob('*.md'))
            if not cards:
                failures.append({'code': 'MISSING_MODEL_CARDS', 'question_id': qid})
            else:
                generic_count = 0
                for card in cards:
                    txt = card.read_text(encoding='utf-8', errors='ignore')
                    if 'Agent must refine' in txt or 'Replace generic card fields' in txt:
                        generic_count += 1
                if generic_count == len(cards):
                    warnings.append({'code': 'MODEL_CARDS_STILL_GENERIC_SCAFFOLD', 'question_id': qid, 'generic_count': generic_count})
    status = 'failed' if failures or (strict and any(w.get('code') == 'MODEL_CARDS_STILL_GENERIC_SCAFFOLD' for w in warnings)) else ('warning' if warnings else 'passed')
    report = {'gate': 'modeling-readiness-check', 'status': status, 'strict': strict, 'evidence': evidence, 'failures': failures, 'warnings': warnings, 'generated_at': now_iso()}
    write_json(case_dir / 'quality' / 'modeling_readiness_report.json', report)
    return report
