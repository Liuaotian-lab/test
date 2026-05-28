from __future__ import annotations
from pathlib import Path
import shutil
from mmos.modeling_os.common import read_json, write_json, status_from


def _proposal_paths(case_dir: Path) -> list[Path]:
    p=case_dir/'workspace'/'routing'/'candidate'/'problem_routing_proposal.json'
    return [p] if p.exists() else []


def routing_check(case_dir: Path, all_routes: bool = True) -> dict:
    case_dir=Path(case_dir).resolve(); failures=[]; warnings=[]; checked=[]
    for path in _proposal_paths(case_dir):
        data=read_json(path, {}) or {}
        checked.append(str(path.relative_to(case_dir)))
        cps=data.get('candidate_paradigms') or []
        if not cps:
            failures.append({'code':'ROUTING_CANDIDATE_PARADIGMS_EMPTY','path':str(path.relative_to(case_dir))})
        for idx, cp in enumerate(cps):
            prefix={'path':str(path.relative_to(case_dir)),'index':idx,'paradigm':cp.get('paradigm')}
            if not cp.get('evidence_ids'):
                failures.append({'code':'ROUTING_PARADIGM_EVIDENCE_MISSING',**prefix})
            if not cp.get('required_validators'):
                failures.append({'code':'ROUTING_REQUIRED_VALIDATORS_MISSING',**prefix})
            if not cp.get('claim_limits'):
                failures.append({'code':'ROUTING_CLAIM_LIMITS_MISSING',**prefix})
            if cp.get('confidence') == 'low' and data.get('requires_human_review') is not True:
                failures.append({'code':'LOW_CONFIDENCE_REQUIRES_HUMAN_REVIEW',**prefix})
        if not data.get('rejected_paradigms'):
            warnings.append({'code':'ROUTING_REJECTED_PARADIGMS_EMPTY','path':str(path.relative_to(case_dir))})
    if not checked:
        failures.append({'code':'ROUTING_PROPOSAL_MISSING','path':'workspace/routing/candidate/problem_routing_proposal.json'})
    report={'status':status_from(failures,warnings),'checked':checked,'failures':failures,'warnings':warnings}
    write_json(case_dir/'workspace'/'routing'/'reports'/'routing_check.json', report)
    return report


def routing_promote(case_dir: Path, all_routes: bool = True) -> dict:
    case_dir=Path(case_dir).resolve()
    check=routing_check(case_dir, all_routes=all_routes)
    failures=[] if check['status']!='failed' else [{'code':'ROUTING_CHECK_FAILED','failures':check.get('failures',[])}]
    outputs=[]
    if not failures:
        src=case_dir/'workspace'/'routing'/'candidate'/'problem_routing_proposal.json'
        dst=case_dir/'workspace'/'routing'/'official'/'problem_routing.json'
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        outputs.append(str(dst.relative_to(case_dir)))
    report={'status':status_from(failures,[]),'outputs':outputs,'failures':failures,'check':check}
    write_json(case_dir/'workspace'/'routing'/'reports'/'routing_promote.json', report)
    return report
