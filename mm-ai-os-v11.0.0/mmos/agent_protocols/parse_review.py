from __future__ import annotations
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from mmos.contracts.manager import upsert_question

REVIEW_CHECKS = [
    'no_missing_questions',
    'no_background_numbering_misclassified',
    'all_required_outputs_identified',
    'dependencies_identified',
    'units_and_data_sources_identified',
    'implicit_tasks_checked',
]


def create_parse_review(case_dir: Path) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    graph_path = case_dir / 'workspace' / 'problem_graph.json'
    graph = read_json(graph_path, {}) or {}
    if not graph:
        return {'status': 'failed', 'code': 'MISSING_PROBLEM_GRAPH', 'message': 'Run problem-parse-v2 first.'}
    write_json(case_dir / 'workspace' / 'problem_graph.raw.json', graph)
    template = {
        'status': 'requires_agent_review',
        'reviewer': 'ai_agent',
        'source_graph': 'workspace/problem_graph.raw.json',
        'checks_required': REVIEW_CHECKS,
        'instructions': [
            'Copy this file to workspace/problem_graph.agent_review.json.',
            'Set status to passed only after checking every item.',
            'If parser missed or misclassified questions, edit reviewed_questions.',
            'Each question must include question_id, title, type, required, source_excerpt, required_outputs, dependencies.',
        ],
        'reviewed_questions': graph.get('questions', []),
        'review_notes': [],
        'generated_at': now_iso(),
    }
    write_json(case_dir / 'workspace' / 'problem_graph.review_template.json', template)
    md = [
        '# Problem Parse Agent Review',
        '',
        'This is a required human/AI-agent semantic review layer over the regex parser.',
        '',
        '## Required checks',
        '',
    ]
    md.extend([f'- {c}' for c in REVIEW_CHECKS])
    md.extend([
        '',
        '## Required action',
        '',
        'Create `workspace/problem_graph.agent_review.json` from the template and set `status: passed` only if the reviewed graph is competition-ready.',
        '',
    ])
    (case_dir / 'workspace' / 'problem_parse_review.md').write_text('\n'.join(md), encoding='utf-8')
    return {'status': 'warning', 'code': 'AGENT_PARSE_REVIEW_REQUIRED', 'template': 'workspace/problem_graph.review_template.json', 'markdown': 'workspace/problem_parse_review.md'}


def apply_parse_review(case_dir: Path, require_passed: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    review_path = case_dir / 'workspace' / 'problem_graph.agent_review.json'
    review = read_json(review_path, {}) or {}
    if not review:
        return {'status': 'failed' if require_passed else 'warning', 'code': 'MISSING_AGENT_PARSE_REVIEW', 'path': 'workspace/problem_graph.agent_review.json'}
    if review.get('status') != 'passed':
        return {'status': 'failed' if require_passed else 'warning', 'code': 'AGENT_PARSE_REVIEW_NOT_PASSED', 'review_status': review.get('status')}
    questions = review.get('reviewed_questions') or review.get('questions') or []
    if not questions:
        return {'status': 'failed', 'code': 'AGENT_PARSE_REVIEW_HAS_NO_QUESTIONS'}
    final_graph = {
        'case_id': case_dir.name,
        'status': 'passed',
        'source': 'agent_review',
        'questions': questions,
        'review_notes': review.get('review_notes', []),
        'generated_at': now_iso(),
    }
    write_json(case_dir / 'workspace' / 'problem_graph.final.json', final_graph)
    # Mirror reviewed questions into the canonical registry.
    for q in questions:
        if q.get('question_id') or q.get('id'):
            upsert_question(case_dir, q)
    return {'status': 'passed', 'question_count': len(questions), 'final_graph': 'workspace/problem_graph.final.json'}


def problem_parse_review(case_dir: Path, apply: bool = False, require_passed: bool = False) -> dict[str, Any]:
    created = create_parse_review(case_dir)
    if apply:
        applied = apply_parse_review(case_dir, require_passed=require_passed)
        return {'status': applied.get('status'), 'created': created, 'applied': applied}
    return created
