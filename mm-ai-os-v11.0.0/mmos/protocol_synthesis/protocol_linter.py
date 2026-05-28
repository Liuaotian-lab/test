from __future__ import annotations
from pathlib import Path
from typing import Any

from mmos.kernel.jsonio import read_json
from mmos.kernel.events import now_iso
from mmos.kernel_gates.common import status_from
from .common import read_protocol, qids, write_report


def protocol_lint(case_dir: Path) -> dict[str, Any]:
    case_dir=Path(case_dir)
    protocol=read_protocol(case_dir)
    failures=[]; warnings=[]
    if not protocol:
        failures.append({'code':'MISSING_OR_INVALID_DOMAIN_PROTOCOL','path':'workspace/dynamic_protocols/candidate/domain_protocol.yaml'})
    else:
        for key in ['protocol_id','case_id','protocol_version','generated_from','questions']:
            if key not in protocol:
                failures.append({'code':'PROTOCOL_MISSING_FIELD','field':key})
        qs=protocol.get('questions') if isinstance(protocol.get('questions'),dict) else {}
        for qid in qids(case_dir):
            if qid not in qs:
                failures.append({'code':'QUESTION_PROTOCOL_MISSING','question_id':qid})
                continue
            q=qs[qid]
            for key in ['objective_summary','matched_capability_atoms','required_model_components','required_certificates','output_requirements','risk_flags']:
                if key not in q:
                    failures.append({'code':'QUESTION_PROTOCOL_MISSING_FIELD','question_id':qid,'field':key})
            comps=q.get('required_model_components') or []
            if not comps:
                failures.append({'code':'NO_MODEL_COMPONENTS','question_id':qid})
            for comp in comps:
                cid=comp.get('component_id')
                for key in ['minimum_fidelity','required_solver_hooks','required_validators','required_negative_tests','claim_limits']:
                    if key not in comp:
                        failures.append({'code':'COMPONENT_MISSING_FIELD','question_id':qid,'component_id':cid,'field':key})
                if not comp.get('required_validators'):
                    failures.append({'code':'COMPONENT_WITHOUT_VALIDATOR','question_id':qid,'component_id':cid})
                if not comp.get('required_negative_tests'):
                    failures.append({'code':'COMPONENT_WITHOUT_NEGATIVE_TEST','question_id':qid,'component_id':cid})
                if comp.get('component_id') in {'optimization_objective','boundary_certificate','global_optimality_certificate'} and not q.get('required_certificates'):
                    failures.append({'code':'STRONG_COMPONENT_WITHOUT_CERTIFICATE','question_id':qid,'component_id':cid})
            if not q.get('output_requirements'):
                failures.append({'code':'OUTPUT_REQUIREMENT_MISSING','question_id':qid})
            if not q.get('matched_capability_atoms'):
                warnings.append({'code':'NO_MATCHED_CAPABILITY_ATOMS','question_id':qid})
    report={'gate':'protocol-lint','status':status_from(failures,warnings),'failures':failures,'warnings':warnings,'generated_at':now_iso()}
    return write_report(case_dir,'workspace/dynamic_protocols/reports/protocol_lint_report.json',report)
