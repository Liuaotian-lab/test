from __future__ import annotations
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import read_json
from mmos.kernel.events import now_iso
from mmos.kernel_gates.common import status_from
from .common import write_report


def dynamic_protocol_gate(case_dir: Path, strict: bool = True) -> dict[str, Any]:
    case_dir=Path(case_dir)
    failures=[]; warnings=[]; checks=[]
    paths={
        'compiled_protocol': case_dir/'workspace'/'dynamic_protocols'/'official'/'compiled_protocol.json',
        'protocol_lint_report': case_dir/'workspace'/'dynamic_protocols'/'reports'/'protocol_lint_report.json',
        'protocol_redteam_report': case_dir/'quality'/'protocol_redteam_report.json',
        'protocol_compile_report': case_dir/'workspace'/'dynamic_protocols'/'reports'/'protocol_compile_report.json',
    }
    for name,p in paths.items():
        checks.append({'check':name,'path':str(p),'exists':p.exists()})
        if not p.exists():
            failures.append({'code':'DYNAMIC_PROTOCOL_ARTIFACT_MISSING','artifact':name,'path':str(p)})
    for name in ['protocol_lint_report','protocol_redteam_report','protocol_compile_report']:
        p=paths[name]
        if p.exists():
            obj=read_json(p,{}) or {}
            if obj.get('status')=='failed':
                failures.append({'code':'DYNAMIC_PROTOCOL_STAGE_FAILED','stage':name,'path':str(p)})
    compiled=read_json(paths['compiled_protocol'],{}) if paths['compiled_protocol'].exists() else {}
    if compiled:
        qcontracts=compiled.get('question_contracts') or {}
        if not qcontracts:
            failures.append({'code':'COMPILED_PROTOCOL_HAS_NO_QUESTION_CONTRACTS'})
        for qid,c in qcontracts.items():
            if not c.get('validators'):
                failures.append({'code':'CONTRACT_WITHOUT_VALIDATORS','question_id':qid})
            if not c.get('negative_tests'):
                failures.append({'code':'CONTRACT_WITHOUT_NEGATIVE_TESTS','question_id':qid})
            if not c.get('fidelity_requirements'):
                failures.append({'code':'CONTRACT_WITHOUT_FIDELITY_REQUIREMENTS','question_id':qid})
    report={'gate':'dynamic-protocol-gate','status':status_from(failures,warnings),'strict':strict,'checks':checks,'failures':failures,'warnings':warnings,'generated_at':now_iso()}
    return write_report(case_dir,'quality/dynamic_protocol_gate_report.json',report)
