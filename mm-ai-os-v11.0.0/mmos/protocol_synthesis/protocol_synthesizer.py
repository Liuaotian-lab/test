from __future__ import annotations
from pathlib import Path
from typing import Any
import json

from mmos.kernel.jsonio import read_json
from mmos.kernel.events import now_iso
from .atom_matcher import capability_atom_match
from .common import qids, unique


def _highest_claim_limit(components: list[dict[str, Any]]) -> str:
    order={'exploratory':0,'approximate':1,'simulation_estimate':1,'evaluated_best':2,'certified_optimal':3,'global_optimal':4}
    if not components:
        return 'exploratory'
    best=max(components, key=lambda c: order.get(str((c.get('claim_limits') or {}).get('max_quality_level', c.get('claim_limit','approximate'))),1))
    return str((best.get('claim_limits') or {}).get('max_quality_level', best.get('claim_limit','approximate')))


def protocol_synthesize(root: Path, case_dir: Path) -> dict[str, Any]:
    root=Path(root); case_dir=Path(case_dir)
    match_path=case_dir/'workspace'/'dynamic_protocols'/'candidate'/'capability_atom_match.json'
    if not match_path.exists():
        capability_atom_match(root, case_dir)
    match=read_json(match_path,{}) or {}
    atoms=match.get('matched_atoms') or []
    certs=unique(c for a in atoms for c in (a.get('required_certificates') or []))
    if any(a.get('atom_id')=='optimization_objective' for a in atoms) and 'candidate_search_certificate' not in certs:
        certs.append('candidate_search_certificate')
    questions={}
    for qid in qids(case_dir):
        components=[]
        for a in atoms:
            components.append({
                'component_id':a['atom_id'],
                'source_constraints':['constraint_ledger','problem_statement'],
                'minimum_fidelity':a.get('minimum_fidelity','L1'),
                'required_solver_hooks':a.get('required_solver_hooks') or [],
                'required_validators':a.get('required_validators') or [],
                'required_negative_tests':a.get('required_negative_tests') or [],
                'claim_limits':{'max_quality_level':a.get('claim_limit','approximate'), 'global_optimality_allowed': a.get('claim_limit')=='global_optimal'}
            })
        questions[qid]={
            'objective_summary': f'Dynamically generated modeling protocol for {qid}.',
            'matched_capability_atoms':[{'atom_id':a['atom_id'],'confidence':a.get('confidence',0.0),'evidence_ids':a.get('evidence_ids',[])} for a in atoms],
            'required_model_components':components,
            'required_certificates':[{'certificate_type':c,'trigger_claims':['optimal','maximum','minimum','boundary','critical','最优','最大','最小','边界','临界'], 'required_for_final': True} for c in certs],
            'output_requirements':[{'artifact_type':'case_outputs','required_validator':'output_schema_validator'}],
            'risk_flags':[{'flag_id':'dynamic_protocol_generated','severity':'medium','mitigation':'protocol_lint_and_redteam_required'}],
            'claim_limits':{'max_quality_level':_highest_claim_limit(components), 'global_optimality_allowed': any(c in {'global_optimality_certificate','exhaustive_enumeration_certificate'} for c in certs)}
        }
    protocol={
        'protocol_id':f'dynamic_protocol_{case_dir.name}',
        'case_id':case_dir.name,
        'protocol_version':1,
        'schema_version':'10.1.dynamic_protocol',
        'generated_from':['problem_type_inference','constraint_ledger','dependency_graph','output_templates','capability_atom_match'],
        'questions':questions,
        'generated_at':now_iso(),
    }
    out=case_dir/'workspace'/'dynamic_protocols'/'candidate'/'domain_protocol.yaml'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(protocol,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {'status':'passed','path':str(out),'protocol_id':protocol['protocol_id'],'question_count':len(questions)}
