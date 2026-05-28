from __future__ import annotations
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import read_json, write_json

CEILING_ORDER = ['not_submit','D','C','B','A-','A','national_first_candidate']

def _min_ceiling(a: str, b: str) -> str:
    return a if CEILING_ORDER.index(a) <= CEILING_ORDER.index(b) else b

def _load(case_dir: Path, rel: str) -> dict[str, Any]:
    return read_json(case_dir / rel, {}) or {}

def award_readiness_check(case_dir: Path, target: str='national_first', strict_submission: bool=False) -> dict[str, Any]:
    case_dir=Path(case_dir).resolve()
    checks={
        'semantic_audit': _load(case_dir, 'quality/semantic_audit.json'),
        'claim_evidence': _load(case_dir, 'quality/claim_evidence_check.json'),
        'solver_variant': _load(case_dir, 'quality/solver_variant_verify.json'),
        'paper_argument': _load(case_dir, 'quality/paper_argument_check.json'),
        'paper_evidence': _load(case_dir, 'quality/paper_evidence_check.json'),
        'figure_argument': _load(case_dir, 'quality/figure_argument_check.json'),
        'submission_gate': _load(case_dir, 'quality/submission_gate.json'),
    }
    ceiling='national_first_candidate'; reasons=[]; repair=[]; major=[]; minor=[]
    def cap(new_ceiling, code, message, action):
        nonlocal ceiling
        ceiling=_min_ceiling(ceiling, new_ceiling)
        item={'code':code,'message':message,'cap':new_ceiling}
        if new_ceiling in {'not_submit','D','C','B'}: major.append(item)
        else: minor.append(item)
        reasons.append(message); repair.append(action)
    sem=checks['semantic_audit']
    if not sem:
        cap('C','SEMANTIC_AUDIT_MISSING','Semantic audit has not been run;题意/变量/约束/单位风险未审计。','Run semantic-audit --all --strict and resolve P0/P1 semantic risks.')
    elif sem.get('status')=='failed':
        cap('not_submit','SEMANTIC_AUDIT_FAILED','Semantic audit failed;作品存在结构性题意理解风险。','Fix problem graph/data manifest and rerun semantic-audit.')
    elif sem.get('high_risk_count',0)>0:
        cap('A-','SEMANTIC_HIGH_RISKS','Semantic audit has unresolved high-risk items; may still be contest-usable but not first-prize safe.','Map each P1 semantic risk to solver/verifier/paper evidence.')
    ce=checks['claim_evidence']
    if not ce:
        cap('B','CLAIM_EVIDENCE_MISSING','Claim-evidence check missing;关键结论没有证据链审计。','Run claim-evidence-plan/check and add evidence for optimality/stability/robustness claims.')
    elif ce.get('status')=='failed':
        cap('B','UNSUPPORTED_CRITICAL_CLAIMS','Critical claims lack required evidence.','Remove unsupported claims or add optimization traces, constraints, and independent verification.')
    sv=checks['solver_variant']
    if not sv:
        cap('B','SOLVER_VARIANTS_UNVERIFIED','Runnable solver variants were not verified.','Run solver-variant-verify --all --strict; variants must have code/log/hash/output.')
    elif sv.get('status')=='failed':
        cap('B','NON_RUNNABLE_SOLVER_VARIANTS','Some solver variants are JSON-only or not reproducible.','Bind every tournament variant to executable code, runtime log, output hash and objective trace.')
    pa=checks['paper_argument']
    if not pa:
        cap('B','PAPER_ARGUMENT_MISSING','Paper argument check missing;论文论证质量未知。','Run paper-argument-check --strict and complete missing sections/formula chain/figures.')
    elif pa.get('status')=='failed':
        cap('B','PAPER_ARGUMENT_WEAK','Paper lacks required contest argument structure or coverage.','Add missing sections, formula chain, Q coverage and argument figures.')
    pe=checks['paper_evidence']
    if not pe:
        cap('B','PAPER_EVIDENCE_MISSING','Paper evidence trace check missing.','Run paper-evidence-check --strict and link numeric claims to result files/logs/verifiers.')
    elif pe.get('status')=='failed':
        cap('B','PAPER_EVIDENCE_WEAK','Paper numeric claims are weakly tied to reproducible evidence.','Add result-to-text traceability and cite output artifacts in paper source comments/manifests.')
    fa=checks['figure_argument']
    if not fa:
        cap('A-','FIGURE_ARGUMENT_MISSING','Figure argument check missing;图表说服力未知。','Run figure-argument-check --strict and add figure manifest with source scripts and supported arguments.')
    elif fa.get('status')=='failed':
        cap('A-','FIGURE_ARGUMENT_WEAK','Figures are missing argument/data/source traceability.','Add figure source scripts, manifest, and tie each figure to a paper claim.')
    sg=checks['submission_gate']
    if strict_submission:
        if not sg:
            cap('C','SUBMISSION_GATE_MISSING','Submission gate missing.','Run submission-gate-check.')
        elif sg.get('status')!='passed':
            cap('not_submit','SUBMISSION_GATE_FAILED','Submission package is not safe to submit.','Fix output/report/PDF/package issues before award evaluation.')
    status='failed' if ceiling in {'not_submit','D'} else ('warning' if ceiling not in {'A','national_first_candidate'} else 'passed')
    result={
        'gate':'award-readiness-check', 'status': status, 'target': target,
        'current_award_ceiling': ceiling, 'confidence': 'medium' if status!='failed' else 'high',
        'blocking_reasons': reasons, 'major_deductions': major, 'minor_deductions': minor,
        'repair_actions': sorted(set(repair)), 'checks_seen': {k: bool(v) for k,v in checks.items()},
        'note': 'Reference-free award ceiling: no historical answer ranges are used.'
    }
    write_json(case_dir/'quality'/'award_readiness.json', result)
    write_json(case_dir/'.agent'/'gate_reports'/'award_readiness.json', result)
    return result
