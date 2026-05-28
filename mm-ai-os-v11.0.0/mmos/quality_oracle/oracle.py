from __future__ import annotations
from pathlib import Path
from mmos.kernel.events import now_iso
from mmos.kernel.jsonio import read_json
from .common import ensure_quality_dirs, write_report

WEIGHTS = {
    'problem_coverage': 10,
    'data_audit': 8,
    'model_maturity': 14,
    'constraint_completeness': 10,
    'solver_strength': 13,
    'independent_verification': 12,
    'sensitivity_robustness': 8,
    'convergence': 7,
    'optimism_control': 8,
    'output_integrity': 5,
    'paper_quality': 3,
    'quality_claim_consistency': 2,
}


def _score_status(status: str | None) -> float:
    return {'passed':1.0,'ok':1.0,'warning':0.55,'partial':0.40,'failed':0.0}.get(status or '',0.25)


def _artifact_status(report: dict, path_exists: bool) -> float:
    if not path_exists:
        return 0.0
    return _score_status(report.get('status'))


def _apply_caps(score: float, confidence: str, decision: str, caps: list[dict]) -> tuple[float, str, str]:
    max_score = score
    max_conf = confidence
    for cap in caps:
        if cap.get('max_score') is not None:
            max_score = min(max_score, float(cap['max_score']))
        if cap.get('max_confidence') == 'moderate' and max_conf == 'high':
            max_conf = 'moderate'
        if cap.get('max_confidence') == 'low':
            max_conf = 'low'
    if max_score < 70:
        return max_score, 'low', 'partial_required'
    if max_score < 85:
        return max_score, min_conf(max_conf, 'moderate'), 'deliverable_with_moderate_confidence'
    if max_conf != 'high':
        return max_score, max_conf, 'deliverable_with_moderate_confidence'
    if max_score < 95:
        return max_score, 'high', 'high_quality_competition_solution'
    return max_score, 'high', 'strong_solution_with_no_unverified_overclaim'


def min_conf(a: str, b: str) -> str:
    order={'low':0,'moderate':1,'high':2}
    return a if order.get(a,0) <= order.get(b,0) else b


def quality_oracle(case_dir: Path, question_id: str | None = None) -> dict:
    case_dir=Path(case_dir).resolve(); ensure_quality_dirs(case_dir)
    paths={
        'problem': case_dir/'workspace'/'problem_graph.json',
        'data': case_dir/'data'/'manifest'/'data_manifest.json',
        'maturity': case_dir/'quality'/'model_maturity_report.json',
        'bound': case_dir/'quality'/'bound_check_report.json',
        'tour': case_dir/'quality'/'solver_tournament_report.json',
        'indep': case_dir/'quality'/'independent_verification_report.json',
        'sens': case_dir/'quality'/'sensitivity_report.json',
        'conv': case_dir/'quality'/'convergence_check_report.json',
        'optimism': case_dir/'quality'/'optimism_risk_report.json',
        'outv': case_dir/'final_outputs'/'output_validation_report.json',
        'red': case_dir/'quality'/'red_team_review.json',
        'report': case_dir/'.agent'/'gate_reports'/'report_consistency.json',
        'report_alt': case_dir/'.agent'/'gate_reports'/'report_consistency_check.json',
        'paper_quality': case_dir/'quality'/'paper_quality_report.json',
    }
    maturity = read_json(paths['maturity'], {}) or {}
    bound = read_json(paths['bound'], {}) or {}
    tour = read_json(paths['tour'], {}) or {}
    indep = read_json(paths['indep'], {}) or {}
    sens = read_json(paths['sens'], {}) or {}
    conv = read_json(paths['conv'], {}) or {}
    optimism = read_json(paths['optimism'], {}) or {}
    outv = read_json(paths['outv'], {}) or read_json(case_dir/'quality'/'output_validation_report.json', {}) or {}
    red = read_json(paths['red'], {}) or {}
    report_consistency = read_json(paths['report'], {}) or read_json(paths['report_alt'], {}) or {}
    paper_quality = read_json(paths['paper_quality'], {}) or {}
    components = {
        'problem_coverage': 1.0 if paths['problem'].exists() else 0.0,
        'data_audit': 1.0 if paths['data'].exists() or (case_dir/'workspace'/'problem_corpus.json').exists() else 0.35,
        'model_maturity': _artifact_status(maturity, paths['maturity'].exists()),
        'constraint_completeness': _artifact_status(bound, paths['bound'].exists()),
        'solver_strength': _artifact_status(tour, paths['tour'].exists()),
        'independent_verification': _artifact_status(indep, paths['indep'].exists()),
        'sensitivity_robustness': _artifact_status(sens, paths['sens'].exists()),
        'convergence': _artifact_status(conv, paths['conv'].exists()),
        'optimism_control': _artifact_status(optimism, paths['optimism'].exists()),
        'output_integrity': _artifact_status(outv, paths['outv'].exists()),
        'paper_quality': _artifact_status(paper_quality, paths['paper_quality'].exists()) if paths['paper_quality'].exists() else (_score_status(report_consistency.get('status')) if (paths['report'].exists() or paths['report_alt'].exists()) else 0.0),
        'quality_claim_consistency': 0.0 if red.get('status') == 'failed' else (0.45 if red.get('status') == 'warning' else (1.0 if paths['red'].exists() else 0.35)),
    }
    raw_score = sum(WEIGHTS[k]*components[k] for k in WEIGHTS)
    caps=[]
    if tour.get('status') == 'warning':
        caps.append({'reason':'solver_tournament_warning_or_insufficient_diversity','max_score':85,'max_confidence':'moderate'})
    if indep.get('status') != 'passed':
        caps.append({'reason':'independent_verification_not_passed','max_score':88,'max_confidence':'moderate'})
    if conv.get('status') == 'warning':
        caps.append({'reason':'convergence_not_established','max_score':85,'max_confidence':'moderate'})
    if optimism.get('status') == 'warning':
        caps.append({'reason':'optimism_risk_open','max_score':85,'max_confidence':'moderate'})
    if optimism.get('status') == 'failed' or red.get('status') == 'failed':
        caps.append({'reason':'blocking_red_team_or_optimism_risk','max_score':69,'max_confidence':'low'})
    if raw_score < 70:
        decision='partial_required'; confidence='low'
    elif raw_score < 85:
        decision='deliverable_with_moderate_confidence'; confidence='moderate'
    elif raw_score < 95:
        decision='high_quality_competition_solution'; confidence='high'
    else:
        decision='strong_solution_with_no_unverified_overclaim'; confidence='high'
    score, confidence, decision = _apply_caps(raw_score, confidence, decision, caps)
    status='failed' if score < 70 else ('warning' if score < 85 or confidence != 'high' else 'passed')
    result={'gate':'quality-oracle-v2','status':status, 'raw_surrogate_score':round(raw_score,2), 'surrogate_score':round(score,2),'confidence':confidence,'decision':decision,'caps_applied':caps,'components':{k:{'weight':WEIGHTS[k],'normalized_score':round(components[k],3),'weighted':round(WEIGHTS[k]*components[k],2)} for k in WEIGHTS},'generated_at':now_iso()}
    md = render_quality_md(result)
    (case_dir/'quality'/'surrogate_quality_report.md').write_text(md, encoding='utf-8')
    return write_report(case_dir, 'surrogate_quality_report.json', result)


def render_quality_md(r: dict) -> str:
    lines=[f"# Surrogate Quality Report v2", '', f"- status: `{r.get('status')}`", f"- raw_score: **{r.get('raw_surrogate_score')} / 100**", f"- capped_score: **{r.get('surrogate_score')} / 100**", f"- confidence: `{r.get('confidence')}`", f"- decision: `{r.get('decision')}`", '']
    if r.get('caps_applied'):
        lines.append('## Quality Caps Applied')
        for c in r['caps_applied']:
            lines.append(f"- {c.get('reason')}: max_score={c.get('max_score')} max_confidence={c.get('max_confidence')}")
        lines.append('')
    lines.extend(['| dimension | weight | normalized | weighted |','|---|---:|---:|---:|'])
    for k,v in r.get('components',{}).items():
        lines.append(f"| {k} | {v['weight']} | {v['normalized_score']} | {v['weighted']} |")
    return '\n'.join(lines)+'\n'
