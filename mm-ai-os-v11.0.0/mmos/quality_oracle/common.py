from __future__ import annotations
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import read_json, write_json

QUALITY_LEVEL_SCORE = {
    'global_optimal': 1.00,
    'certified_optimal': 0.96,
    'exhaustive_best': 0.90,
    'local_optimal': 0.74,
    'heuristic_feasible': 0.72,
    'evaluated_best': 0.70,
    'simulation_estimate': 0.66,
    'approximate': 0.52,
    'exploratory': 0.30,
    'failed': 0.00,
}

MODEL_LEVEL_SCORE = {'L0':0.0,'L1':0.22,'L2':0.42,'L3':0.66,'L4':0.84,'L5':1.0}


def ensure_quality_dirs(case_dir: Path) -> None:
    for rel in ['quality','quality/intermediate','quality/tournament','quality/red_team','quality/improvements','results']:
        (Path(case_dir)/rel).mkdir(parents=True, exist_ok=True)


def registry_questions(case_dir: Path) -> list[dict[str, Any]]:
    reg = read_json(Path(case_dir)/'registry'/'questions_registry.json', {'questions': []}) or {'questions': []}
    return [q for q in reg.get('questions', []) if q.get('required', True) is not False]


def question_ids(case_dir: Path, question_id: str | None = None) -> list[str]:
    if question_id:
        return [question_id]
    return [(q.get('question_id') or q.get('id')) for q in registry_questions(case_dir) if (q.get('question_id') or q.get('id'))]


def read_solution(case_dir: Path, qid: str) -> dict[str, Any]:
    path = Path(case_dir)/'results'/qid/'outputs'/'solution_real.json'
    return read_json(path, {}) or {}


def write_report(case_dir: Path, name: str, report: dict[str, Any]) -> dict[str, Any]:
    ensure_quality_dirs(Path(case_dir))
    write_json(Path(case_dir)/'quality'/name, report)
    return report


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ['| ' + ' | '.join(headers) + ' |', '|' + '|'.join(['---']*len(headers)) + '|']
    for row in rows:
        out.append('| ' + ' | '.join(str(x) for x in row) + ' |')
    return '\n'.join(out)
