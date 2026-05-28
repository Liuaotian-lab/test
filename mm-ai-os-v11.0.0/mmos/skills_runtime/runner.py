from __future__ import annotations
from pathlib import Path
from fnmatch import fnmatch
from mmos.modeling_os.common import write_json, now_iso, status_from
from .manifest import load_manifest, validate_manifest
from .context_budget import evaluate_context_budget


def _allowed(rel: str, patterns: list[str]) -> bool:
    return any(fnmatch(rel, pat) for pat in patterns)


def _default_problem_router_output(case_dir: Path, rel: str) -> None:
    out=case_dir/rel
    write_json(out, {
        'case_id': case_dir.name,
        'question_id': 'Q1',
        'routing_id': 'Q1_route_001',
        'candidate_paradigms': [{
            'paradigm':'deterministic_simulation',
            'capabilities':['simulation'],
            'evidence_ids':['ev_skill_runtime_default'],
            'why':'Generated as a deterministic candidate route scaffold; replace with problem-specific evidence before promotion.',
            'required_validators':['output_template_check','domain_validate'],
            'claim_limits':['No optimality claim without certificate.'],
            'confidence':'medium'
        }],
        'rejected_paradigms':[],
        'requires_human_review': False,
    })


def run_skill(root: Path, case_dir: Path, skill_id: str) -> dict:
    root=Path(root).resolve(); case_dir=Path(case_dir).resolve()
    failures=[]; warnings=[]
    try:
        manifest=load_manifest(root, skill_id)
    except FileNotFoundError as exc:
        report={'status':'failed','skill_id':skill_id,'failures':[{'code':'SKILL_MANIFEST_MISSING','message':str(exc)}], 'warnings':[]}
        return report
    mv=validate_manifest(manifest)
    failures.extend(mv.get('failures',[]))
    budget=evaluate_context_budget(case_dir, manifest)
    if budget['status']=='failed':
        failures.extend(budget['failures'])
    outputs=[]
    if not failures:
        for rel in manifest.get('required_outputs') or []:
            if not _allowed(rel, manifest.get('allowed_write_paths') or []):
                failures.append({'code':'SKILL_OUTPUT_NOT_ALLOWED','path':rel})
                continue
            if skill_id == 'problem_router' and rel.endswith('problem_routing_proposal.json'):
                _default_problem_router_output(case_dir, rel)
            else:
                write_json(case_dir/rel, {'skill_id':skill_id,'status':'candidate_generated','created_at':now_iso()})
            outputs.append(rel)
    missing=[]
    for rel in manifest.get('required_outputs') or []:
        if not (case_dir/rel).exists():
            missing.append(rel)
    if missing:
        failures.append({'code':'SKILL_REQUIRED_OUTPUT_MISSING','paths':missing})
    report={'skill_id':skill_id,'run_id':f'run_{now_iso().replace(":", "").replace("+", "Z")}', 'case_id':case_dir.name, 'loaded_files':budget.get('loaded_files',[]), 'context_budget':budget, 'outputs':outputs, 'gates':manifest.get('required_gates') or [], 'status':status_from(failures,warnings), 'failures':failures, 'warnings':warnings}
    write_json(case_dir/'.agent'/'skill_reports'/f'{skill_id}_{report["run_id"]}.json', report)
    return report


def check_skill(root: Path, case_dir: Path, skill_id: str) -> dict:
    try:
        manifest=load_manifest(root, skill_id)
    except FileNotFoundError as exc:
        return {'status':'failed','skill_id':skill_id,'failures':[{'code':'SKILL_MANIFEST_MISSING','message':str(exc)}], 'warnings':[]}
    failures=validate_manifest(manifest).get('failures',[])
    for rel in manifest.get('required_outputs') or []:
        if not (Path(case_dir)/rel).exists():
            failures.append({'code':'SKILL_REQUIRED_OUTPUT_MISSING','path':rel})
    return {'status':status_from(failures,[]),'skill_id':skill_id,'failures':failures,'warnings':[]}
