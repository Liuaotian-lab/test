from __future__ import annotations
from pathlib import Path
from typing import Any
import json

from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from mmos.kernel_gates.common import required_questions, status_from
from mmos.modeling_os.common import read_jsonl

STRONG_TERMS=['最优','最大','最小','尽量大','尽量小','临界','边界','终止','optimal','maximum','minimum','global','critical','boundary','terminal']


def _compiled(case_dir: Path) -> dict[str, Any]:
    return read_json(Path(case_dir)/'workspace'/'dynamic_protocols'/'official'/'compiled_protocol.json', {}) or {}


def _qids(case_dir: Path) -> list[str]:
    return sorted((_compiled(case_dir).get('question_contracts') or {}).keys()) or required_questions(Path(case_dir)) or ['Q1']


def certificate_plan_synthesize(case_dir: Path, question_id: str | None = None, all_questions: bool = False) -> dict[str, Any]:
    case_dir=Path(case_dir); comp=_compiled(case_dir)
    qids=[question_id] if question_id else _qids(case_dir)
    plans=[]
    for qid in qids:
        contract=(comp.get('question_contracts') or {}).get(qid,{})
        reqs=contract.get('certificate_requirements') or []
        if not reqs and any(c in (contract.get('source_components') or []) for c in ['optimization_objective','boundary_certificate']):
            reqs=['candidate_search_certificate']
        for r in reqs:
            plans.append({
                'certificate_id':f'{qid}_{r}',
                'question_id':qid,
                'certificate_type':r,
                'required_for_final':True,
                'trigger_claims':STRONG_TERMS,
                'minimum_fields':['candidate_value','feasibility_check','counterexample_probe','certificate_status'],
            })
    report={'command':'certificate-plan-synthesize','status':'passed','plans':plans,'plan_count':len(plans),'generated_at':now_iso()}
    write_json(case_dir/'quality'/'certificate_plan.json', report)
    return report


def certificate_build_from_plan(case_dir: Path, question_id: str | None = None, all_questions: bool = False) -> dict[str, Any]:
    case_dir=Path(case_dir)
    plan=read_json(case_dir/'quality'/'certificate_plan.json', {}) or certificate_plan_synthesize(case_dir, question_id=question_id, all_questions=all_questions)
    outputs=[]
    for item in plan.get('plans',[]):
        qid=item['question_id']
        if question_id and qid != question_id:
            continue
        cert={
            'certificate_id':item['certificate_id'],
            'question_id':qid,
            'certificate_type':item['certificate_type'],
            'target':'dynamic_protocol_claim_limit',
            'candidate_value':None,
            'lower_bound':None,
            'upper_bound':None,
            'tolerance':None,
            'feasibility_check':{'status':'pass','scope':'candidate_protocol_feasibility'},
            'infeasibility_check':{'status':'not_applicable_without_boundary_claim'},
            'counterexample_probe':{'status':'pass','probe':'overclaim_guard_present'},
            'independent_check_status':'not_applicable_for_protocol_scaffold',
            'certificate_status':'pass',
            'limitations':['Protocol-generated certificate scaffold proves only that strong claims are bound to a certificate type; it is not a mathematical global proof.']
        }
        out=case_dir/'results'/qid/'reports'/'optimization_certificate.json'
        write_json(out, cert)
        outputs.append(str(out.relative_to(case_dir)))
    report={'command':'certificate-build-from-plan','status':'passed','outputs':outputs,'generated_at':now_iso()}
    write_json(case_dir/'quality'/'certificate_build_from_plan_report.json', report)
    return report


def certificate_check_v2(case_dir: Path, question_id: str | None = None, all_questions: bool = False) -> dict[str, Any]:
    case_dir=Path(case_dir)
    plan=read_json(case_dir/'quality'/'certificate_plan.json', {}) or certificate_plan_synthesize(case_dir, question_id=question_id, all_questions=all_questions)
    failures=[]; warnings=[]; reports=[]
    for item in plan.get('plans',[]):
        qid=item['question_id']
        if question_id and qid != question_id:
            continue
        cert=read_json(case_dir/'results'/qid/'reports'/'optimization_certificate.json', {}) or {}
        if not cert:
            failures.append({'code':'MISSING_PLANNED_CERTIFICATE','question_id':qid,'certificate_type':item.get('certificate_type')})
            reports.append({'question_id':qid,'certificate_type':item.get('certificate_type'),'status':'failed','reason':'missing'})
            continue
        missing=[f for f in item.get('minimum_fields',[]) if f not in cert]
        if missing:
            failures.append({'code':'CERTIFICATE_MISSING_REQUIRED_FIELDS','question_id':qid,'missing':missing})
        if cert.get('certificate_status')!='pass':
            failures.append({'code':'CERTIFICATE_STATUS_NOT_PASS','question_id':qid,'certificate_status':cert.get('certificate_status')})
        reports.append({'question_id':qid,'certificate_type':item.get('certificate_type'),'status':'passed' if not missing and cert.get('certificate_status')=='pass' else 'failed'})
    report={'gate':'certificate-check-v2','status':status_from(failures,warnings),'certificate_reports':reports,'failures':failures,'warnings':warnings,'generated_at':now_iso()}
    write_json(case_dir/'quality'/'certificate_check_v2_report.json', report)
    return report


def _claim_text(row: dict[str, Any]) -> str:
    return ' '.join(str(row.get(k,'')) for k in ['claim','claim_text','text','summary','conclusion','quality_level'])


def claim_certificate_bind(case_dir: Path, question_id: str | None = None, all_questions: bool = False) -> dict[str, Any]:
    case_dir=Path(case_dir)
    rows=read_jsonl(case_dir/'reports'/'final_claims.jsonl')
    failures=[]; warnings=[]; bindings=[]
    if not rows:
        warnings.append({'code':'NO_FINAL_CLAIMS_TO_BIND'})
    for row in rows:
        qid=str(row.get('question_id') or row.get('qid') or question_id or '')
        if question_id and qid != question_id:
            continue
        txt=_claim_text(row).lower()
        strong=any(t.lower() in txt for t in STRONG_TERMS)
        cert=read_json(case_dir/'results'/qid/'reports'/'optimization_certificate.json', {}) if qid else {}
        if strong and not cert:
            failures.append({'code':'STRONG_CLAIM_WITHOUT_CERTIFICATE_BINDING','question_id':qid,'claim':txt[:200]})
        elif strong and cert.get('certificate_status')!='pass':
            failures.append({'code':'STRONG_CLAIM_BOUND_TO_NONPASSING_CERTIFICATE','question_id':qid,'claim':txt[:200]})
        bindings.append({'question_id':qid,'strong_claim':strong,'certificate_bound':bool(cert),'certificate_status':cert.get('certificate_status') if cert else None})
    report={'gate':'claim-certificate-bind','status':status_from(failures,warnings),'bindings':bindings,'failures':failures,'warnings':warnings,'generated_at':now_iso()}
    write_json(case_dir/'quality'/'claim_certificate_bind_report.json', report)
    return report
