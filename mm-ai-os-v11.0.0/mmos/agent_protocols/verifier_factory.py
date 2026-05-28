from __future__ import annotations
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import write_json
from mmos.kernel.events import now_iso
from mmos.quality_oracle.common import question_ids
from mmos.agent_protocols.verifiers import scaffold_verifier

VERIFIER_SPECS = {
    'constraint_verifier': 'Recompute hard constraints and feasibility from raw data/final outputs without importing solve.py.',
    'metric_recompute': 'Recompute the headline objective/metric by an independent formula or script.',
    'alternative_solver_check': 'Use an alternative algorithm/formulation on a reduced or full instance and compare key values.',
}


def verifier_factory(case_dir: Path, question_id: str | None = None, force: bool = False, target: str = 'first_prize') -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    base = scaffold_verifier(case_dir, question_id=question_id, force=force)
    created=[]; failures=[]
    qids = question_ids(case_dir, question_id)
    if not qids:
        failures.append({'code': 'NO_REQUIRED_QUESTIONS'})
    for qid in qids:
        vdir = case_dir / 'engineering' / 'questions' / qid / 'verifiers'
        vdir.mkdir(parents=True, exist_ok=True)
        for name, desc in VERIFIER_SPECS.items():
            spec = vdir / f'{name}_spec.md'
            if force or not spec.exists():
                spec.write_text(f"""# {qid} {name} Spec

- target: `{target}`
- verifier_type: `{name}`

## Requirement
{desc}

## Non-negotiable independence rule
The verifier must not import the main solver or read hidden intermediate variables.
It should read raw data and/or final registered outputs only.

## Required JSON output fields
- status
- question_id
- verifier
- method
- solver_value
- recomputed_value
- abs_error
- rel_error
- tolerance
- failure
""", encoding='utf-8')
            created.append(str(spec.relative_to(case_dir)))
    report = {'status': 'failed' if failures else 'ok', 'target': target, 'base_scaffold': base, 'created': created, 'failures': failures, 'generated_at': now_iso()}
    write_json(case_dir / 'quality' / 'verifier_factory_report.json', report)
    return report
