from __future__ import annotations
from pathlib import Path
from typing import Any

from mmos.kernel.jsonio import write_json
from mmos.kernel_gates.common import status_from


def _collect(name: str, report: dict[str, Any]) -> dict[str, Any]:
    return {'gate':name,'status':report.get('status'),'report':report}


def _failures_from(name: str, report: dict[str, Any], *, hard_warning: bool = False) -> list[dict[str, Any]]:
    if report.get('status') == 'failed' or (hard_warning and report.get('status') == 'warning'):
        issues = report.get('failures') or ([] if report.get('status') != 'warning' else report.get('warnings') or [{'code':'WARNING_TREATED_AS_BLOCKING'}])
        out=[]
        for f in issues or [{'code':'GATE_FAILED'}]:
            d=dict(f) if isinstance(f,dict) else {'message':str(f)}
            d.setdefault('source',name)
            out.append(d)
        return out
    return []


def final_gate_v3(case_dir: Path, *, root: Path | None = None, strict: bool = True) -> dict[str, Any]:
    case_dir=Path(case_dir)
    from mmos.final_gate_v2.final_gate import final_gate_v2
    from mmos.protocol_synthesis.gate import dynamic_protocol_gate
    from mmos.fidelity.dynamic_fidelity import dynamic_model_fidelity_check, claim_limit_check
    from mmos.dynamic_certificates.planner import certificate_check_v2, claim_certificate_bind
    from mmos.output_schema.dynamic_output_schema import output_schema_check, workbook_schema_validate
    from mmos.heterogeneous_verification.runner import discrepancy_report
    from mmos.os_diagnostics.reports import gate_escape_risk_check, capability_gap_matrix, os_improvement_report

    artifact=[]; validity=[]; trust=[]; dynamic=[]; diagnostics=[]
    artifact.append(_collect('final-gate-v2', final_gate_v2(case_dir, root=root, strict=strict)))
    dynamic.append(_collect('dynamic-protocol-gate', dynamic_protocol_gate(case_dir, strict=strict)))
    dynamic.append(_collect('model-fidelity-check', dynamic_model_fidelity_check(case_dir, strict=strict)))
    dynamic.append(_collect('claim-limit-check', claim_limit_check(case_dir, all_questions=True)))
    if (case_dir/'quality'/'certificate_plan.json').exists() or any((case_dir/'results').glob('*/reports/optimization_certificate.json')):
        trust.append(_collect('certificate-check-v2', certificate_check_v2(case_dir, all_questions=True)))
        trust.append(_collect('claim-certificate-bind', claim_certificate_bind(case_dir, all_questions=True)))
    if (case_dir/'workspace'/'output_schema'/'candidate'/'output_schema.json').exists():
        artifact.append(_collect('output-schema-check', output_schema_check(case_dir)))
        artifact.append(_collect('workbook-schema-validate', workbook_schema_validate(case_dir, all_required=True)))
    if (case_dir/'quality'/'heterogeneous_verify_report.json').exists():
        trust.append(_collect('discrepancy-report', discrepancy_report(case_dir, all_questions=True)))
    diagnostics.append(_collect('gate-escape-risk-check', gate_escape_risk_check(case_dir)))
    diagnostics.append(_collect('capability-gap-matrix', capability_gap_matrix(case_dir, root=root)))
    diagnostics.append(_collect('os-improvement-report', os_improvement_report(case_dir, root=root)))

    failures=[]
    for group in [artifact, validity, trust, dynamic]:
        for item in group:
            failures.extend(_failures_from(item['gate'], item['report']))
    # Diagnostics are not blocking unless they expose high severity risks while strict.
    if strict:
        for item in diagnostics:
            if item['gate']=='gate-escape-risk-check':
                for r in item['report'].get('gate_escape_risks') or []:
                    if r.get('severity')=='high':
                        failures.append({'code':'HIGH_SEVERITY_GATE_ESCAPE_RISK','risk':r.get('risk'),'source':item['gate']})
    report={
        'gate':'final-gate-v3',
        'status':status_from(failures,[]),
        'case_dir':str(case_dir),
        'strict':strict,
        'artifact_gate':'failed' if any(x.get('status')=='failed' for x in artifact) else 'passed',
        'validity_gate':'failed' if any(x.get('status')=='failed' for x in validity) else 'passed',
        'trust_gate':'failed' if any(x.get('status')=='failed' for x in trust) else 'passed',
        'dynamic_protocol_gate':'failed' if any(x.get('status')=='failed' for x in dynamic) else 'passed',
        'diagnostics_gate':'warning' if any(x.get('status')=='warning' for x in diagnostics) else 'passed',
        'gate_results':{'artifact':artifact,'validity':validity,'trust':trust,'dynamic':dynamic,'diagnostics':diagnostics},
        'blocking_issues':failures,
        'failures':failures,
        'warnings':[],
    }
    write_json(case_dir/'quality'/'final_gate_v3_report.json', report)
    write_json(case_dir/'final_outputs'/'final_gate_v3_report.json', report)
    return report
