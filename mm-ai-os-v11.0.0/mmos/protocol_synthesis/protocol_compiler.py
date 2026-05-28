from __future__ import annotations
from pathlib import Path
from typing import Any

from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from mmos.kernel_gates.common import status_from
from .common import read_protocol, unique, write_report
from .protocol_linter import protocol_lint


def protocol_compile(case_dir: Path) -> dict[str, Any]:
    case_dir=Path(case_dir)
    lint=read_json(case_dir/'workspace'/'dynamic_protocols'/'reports'/'protocol_lint_report.json',{}) or protocol_lint(case_dir)
    protocol=read_protocol(case_dir)
    failures=[]; warnings=[]
    if not protocol:
        failures.append({'code':'MISSING_DOMAIN_PROTOCOL'})
    if lint.get('status')=='failed':
        failures.append({'code':'PROTOCOL_LINT_NOT_PASSED'})
    contracts={}
    if protocol:
        for qid,q in (protocol.get('questions') or {}).items():
            comps=q.get('required_model_components') or []
            solver_hooks=unique(h for c in comps for h in (c.get('required_solver_hooks') or []))
            validators=unique(v for c in comps for v in (c.get('required_validators') or []))
            negative=unique(n for c in comps for n in (c.get('required_negative_tests') or []))
            fidelity=[{'component_id':c.get('component_id'), 'minimum_fidelity':c.get('minimum_fidelity','L1'), 'claim_limits':c.get('claim_limits') or {}} for c in comps]
            certs=unique(c.get('certificate_type') for c in (q.get('required_certificates') or []) if c.get('certificate_type'))
            contracts[qid]={
                'question_id':qid,
                'solver_hooks':solver_hooks,
                'validators':validators,
                'negative_tests':negative,
                'certificate_requirements':certs,
                'fidelity_requirements':fidelity,
                'claim_limits':q.get('claim_limits') or {'max_quality_level':'approximate','global_optimality_allowed':False},
                'output_requirements':q.get('output_requirements') or [],
                'source_components':[c.get('component_id') for c in comps],
            }
            # materialize dynamic contracts for existing contract tooling to consume later
            qcontract_dir=case_dir/'contracts'/'questions'/qid
            write_json(qcontract_dir/'dynamic_solver_contract.json', {'question_id':qid,'solver_hooks':solver_hooks})
            write_json(qcontract_dir/'dynamic_validator_contract.json', {'question_id':qid,'validators':validators,'negative_tests':negative})
            write_json(qcontract_dir/'dynamic_certificate_contract.json', {'question_id':qid,'certificate_requirements':certs})
            write_json(qcontract_dir/'dynamic_output_contract.json', {'question_id':qid,'output_requirements':q.get('output_requirements') or []})
            write_json(qcontract_dir/'dynamic_fidelity_contract.json', {'question_id':qid,'fidelity_requirements':fidelity,'claim_limits':q.get('claim_limits') or {}})
    compiled={
        'compiled_protocol_id':f"compiled_{protocol.get('protocol_id','missing')}",
        'case_id':case_dir.name,
        'schema_version':'10.1.compiled_dynamic_protocol',
        'source_protocol':str((case_dir/'workspace'/'dynamic_protocols'/'candidate'/'domain_protocol.yaml').relative_to(case_dir)),
        'question_contracts':contracts,
        'generated_at':now_iso(),
    }
    if failures:
        report={'gate':'protocol-compile','status':'failed','failures':failures,'warnings':warnings,'compiled_contract_count':len(contracts)}
    else:
        out=case_dir/'workspace'/'dynamic_protocols'/'official'/'compiled_protocol.json'
        write_json(out, compiled)
        report={'gate':'protocol-compile','status':'passed','path':str(out),'failures':[],'warnings':warnings,'compiled_contract_count':len(contracts)}
    return write_report(case_dir,'workspace/dynamic_protocols/reports/protocol_compile_report.json',report)
