from __future__ import annotations
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import write_json
from mmos.artifacts.outputs import validate_outputs
from mmos.gates.report_consistency import report_consistency_check
from mmos.paper_excellence.checks import pdf_text_check
from mmos.paper_latex.latex import paper_env_doctor


def submission_gate_check(case_dir: Path, strict_warnings: bool=True) -> dict[str, Any]:
    case_dir=Path(case_dir).resolve(); checks=[]
    def add(name, result):
        checks.append({'name':name,'status':result.get('status'),'result':result})
    add('paper-env-doctor', paper_env_doctor(Path(__file__).resolve().parents[2], case_dir=case_dir))
    add('output-validate', validate_outputs(case_dir, semantic=True, freshness=True))
    add('report-consistency-check', report_consistency_check(case_dir))
    add('pdf-text-check', pdf_text_check(case_dir))
    ok_statuses = {'passed', 'ok', 'ready'}
    failures=[c for c in checks if c.get('status') not in ok_statuses and c.get('status') != 'warning']
    warnings=[c for c in checks if c.get('status')=='warning']
    status='failed' if failures or (strict_warnings and warnings) else 'passed'
    result={'gate':'submission-gate-check','status':status,'submission_allowed':status=='passed','checks':checks,'failure_count':len(failures),'warning_count':len(warnings)}
    write_json(case_dir/'quality'/'submission_gate.json', result)
    write_json(case_dir/'.agent'/'gate_reports'/'submission_gate.json', result)
    return result
