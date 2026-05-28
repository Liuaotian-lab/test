from __future__ import annotations
from pathlib import Path
from typing import Any
import re
from mmos.kernel.jsonio import read_json, write_json

CLAIM_REQUIREMENTS = {
    'optimality': ['optimization_trace','constraint_report'],
    'stability': ['long_run_metrics','robustness_report'],
    'accuracy': ['error_report','independent_recompute'],
    'robustness': ['sensitivity_report','robustness_report'],
    'feasibility': ['constraint_report'],
    'generalization': ['scope_conditions','sensitivity_report'],
    'innovation': ['baseline_comparison'],
}
CLAIM_PATTERNS = {
    'optimality': r'最优|最佳|全局最优|最大化|最小化|optimal',
    'stability': r'稳定|波动|收敛|平稳|stable',
    'accuracy': r'准确|误差|拟合|预测|精度|accuracy',
    'robustness': r'鲁棒|敏感性|扰动|稳健|robust',
    'feasibility': r'满足.*约束|可行|feasible',
    'generalization': r'推广|适用|泛化|general',
    'innovation': r'创新|改进|优于|baseline|对比',
}

def _read_texts(case_dir: Path) -> str:
    parts=[]
    for p in [case_dir / 'paper' / 'main_paper.md', case_dir / 'paper_latex' / 'main.tex']:
        if p.exists(): parts.append(p.read_text(encoding='utf-8', errors='ignore'))
    for p in sorted((case_dir / 'reports').glob('*.md')) if (case_dir / 'reports').exists() else []:
        parts.append(p.read_text(encoding='utf-8', errors='ignore'))
    return '\n'.join(parts)

def _evidence_exists(case_dir: Path, qid: str, evidence_key: str) -> bool:
    patterns = {
        'optimization_trace': [f'results/{qid}/**/*trace*.csv', f'results/{qid}/**/*optimization*.json'],
        'constraint_report': [f'results/{qid}/**/*constraint*.json', f'quality/*constraint*.json'],
        'long_run_metrics': [f'results/{qid}/**/*metrics*.json', f'results/{qid}/solution_real.json'],
        'robustness_report': [f'results/{qid}/**/*robust*.json', f'quality/*robust*.json'],
        'error_report': [f'results/{qid}/**/*error*.json', f'results/{qid}/**/*residual*.json'],
        'independent_recompute': [f'results/{qid}/independent_verification/**/*.json', f'results/{qid}/**/*verifier*.json'],
        'sensitivity_report': [f'results/{qid}/**/*sensitivity*.json', f'quality/*sensitivity*.json'],
        'scope_conditions': [f'contracts/questions/{qid}/assumption_registry.json', f'reports/*{qid}*'],
        'baseline_comparison': [f'results/{qid}/tournament/**/*.json', f'results/{qid}/**/*baseline*.json'],
    }
    for pat in patterns.get(evidence_key, []):
        if list(case_dir.glob(pat)):
            return True
    return False

def claim_evidence_plan(case_dir: Path, question_id: str | None = None) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    graph = read_json(case_dir / 'workspace' / 'problem_graph.json', {}) or read_json(case_dir / 'registry' / 'questions_registry.json', {}) or {'questions': []}
    qs = graph.get('questions', []) or [{'question_id': 'Q1'}]
    if question_id:
        qs = [q for q in qs if q.get('question_id') == question_id]
    text = _read_texts(case_dir)
    out_dir = case_dir / 'workspace' / 'claim_evidence'
    plans=[]
    for q in qs:
        qid=q.get('question_id') or 'Q1'
        qtext=(q.get('source_excerpt') or '') + '\n' + text
        claims=[]
        for ctype, pat in CLAIM_PATTERNS.items():
            if re.search(pat, qtext, flags=re.I):
                claims.append({'claim_type': ctype, 'required_evidence': CLAIM_REQUIREMENTS[ctype]})
        if not claims:
            claims.append({'claim_type': 'feasibility', 'required_evidence': CLAIM_REQUIREMENTS['feasibility']})
        plan={'question_id':qid,'claims':claims,'status':'planned'}
        write_json(out_dir / f'{qid}.claims.json', plan)
        plans.append(plan)
    summary={'status':'passed','case_id':case_dir.name,'question_count':len(plans),'questions':plans}
    write_json(out_dir / 'claims_registry.json', summary)
    return summary

def claim_evidence_check(case_dir: Path, question_id: str | None = None, strict: bool = True) -> dict[str, Any]:
    case_dir=Path(case_dir).resolve()
    plan_path=case_dir / 'workspace' / 'claim_evidence' / 'claims_registry.json'
    plan=read_json(plan_path,{}) or claim_evidence_plan(case_dir, question_id)
    qs=plan.get('questions', [])
    if question_id:
        qs=[q for q in qs if q.get('question_id')==question_id]
    unsupported=[]; evidence_map=[]
    for q in qs:
        qid=q.get('question_id') or 'Q1'
        for claim in q.get('claims', []):
            missing=[]
            for ev in claim.get('required_evidence', []):
                ok=_evidence_exists(case_dir, qid, ev)
                evidence_map.append({'question_id':qid,'claim_type':claim.get('claim_type'),'evidence':ev,'found':ok})
                if not ok: missing.append(ev)
            if missing:
                unsupported.append({'question_id':qid,'claim_type':claim.get('claim_type'),'missing_evidence':missing,'severity':'P1' if claim.get('claim_type') in {'optimality','feasibility'} else 'P2'})
    status='failed' if strict and any(u['severity']=='P1' for u in unsupported) else ('warning' if unsupported else 'passed')
    out_dir=case_dir/'workspace'/'claim_evidence'
    result={'status':status,'case_id':case_dir.name,'unsupported_claim_count':len(unsupported),'unsupported_claims':unsupported,'evidence_map':evidence_map}
    write_json(out_dir/'evidence_map.json', evidence_map)
    write_json(out_dir/'unsupported_claims.json', {'unsupported_claims':unsupported})
    write_json(out_dir/'claim_evidence_report.json', result)
    write_json(case_dir/'quality'/'claim_evidence_check.json', result)
    return result
