from __future__ import annotations
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import read_json
from mmos.kernel.events import now_iso
from mmos.kernel_gates.common import status_from
from .common import read_protocol, case_text, write_report
from .protocol_linter import protocol_lint


def protocol_redteam(case_dir: Path) -> dict[str, Any]:
    case_dir=Path(case_dir)
    lint_path=case_dir/'workspace'/'dynamic_protocols'/'reports'/'protocol_lint_report.json'
    lint=read_json(lint_path,{}) or protocol_lint(case_dir)
    protocol=read_protocol(case_dir)
    failures=[]; warnings=[]; checks=[]
    if lint.get('status')=='failed':
        failures.append({'code':'PROTOCOL_LINT_FAILED','source':'protocol-lint'})
    txt=case_text(case_dir).lower()
    # attack common omissions
    if any(w in txt for w in ['最优','最大','最小','optimal','maximum','minimum']) and protocol:
        for qid,q in (protocol.get('questions') or {}).items():
            if not q.get('required_certificates'):
                failures.append({'code':'OPTIMIZATION_SEMANTICS_WITHOUT_CERTIFICATE','question_id':qid})
    if any(w in txt for w in ['单位','kw','mw','m2','m³','角度','弧度','unit']):
        has_unit=False
        for q in (protocol.get('questions') or {}).values():
            for c in q.get('required_model_components') or []:
                if 'unit' in c.get('component_id','') or any('unit' in v for v in c.get('required_validators') or []):
                    has_unit=True
        if not has_unit:
            failures.append({'code':'UNIT_SEMANTICS_WITHOUT_UNIT_VALIDATOR'})
    if any(w in txt for w in ['xlsx','excel','表','模板','result']):
        for qid,q in (protocol.get('questions') or {}).items():
            if not q.get('output_requirements'):
                failures.append({'code':'OUTPUT_TEMPLATE_WITHOUT_OUTPUT_PROTOCOL','question_id':qid})
    for qid,q in (protocol.get('questions') or {}).items():
        for comp in q.get('required_model_components') or []:
            if not comp.get('minimum_fidelity'):
                failures.append({'code':'MODEL_COMPONENT_WITHOUT_MINIMUM_FIDELITY','question_id':qid,'component_id':comp.get('component_id')})
            lim=comp.get('claim_limits') or {}
            if 'max_quality_level' not in lim:
                failures.append({'code':'MODEL_COMPONENT_WITHOUT_CLAIM_LIMIT','question_id':qid,'component_id':comp.get('component_id')})
    checks.extend([
        'explicit_constraint_coverage_probe','implicit_constraint_probe','unit_semantics_probe','output_template_probe','overclaim_probe','fidelity_probe'
    ])
    report={'gate':'protocol-redteam','status':status_from(failures,warnings),'checks':checks,'blocking_issues':failures,'failures':failures,'warnings':warnings,'generated_at':now_iso()}
    return write_report(case_dir,'quality/protocol_redteam_report.json',report)
