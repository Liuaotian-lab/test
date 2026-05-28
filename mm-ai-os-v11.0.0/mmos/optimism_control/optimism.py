from __future__ import annotations
from pathlib import Path
from mmos.kernel.events import now_iso
from mmos.kernel.jsonio import read_json, write_json
from mmos.quality_oracle.common import ensure_quality_dirs, question_ids, read_solution, write_report


def _metric(sol: dict, keys=('improvement_ratio','improvement','gain_ratio','objective_value','score','value')):
    for k in keys:
        if isinstance(sol.get(k), (int, float)):
            return k, float(sol[k])
    metrics = sol.get('metrics') or {}
    if isinstance(metrics, dict):
        for k in keys:
            if isinstance(metrics.get(k), (int,float)):
                return f'metrics.{k}', float(metrics[k])
    return None, None


def optimism_risk_check(case_dir: Path, question_id: str | None = None) -> dict:
    case_dir=Path(case_dir).resolve(); ensure_quality_dirs(case_dir)
    findings=[]; questions={}
    tour = read_json(case_dir/'quality'/'solver_tournament_report.json', {}) or {}
    indep = read_json(case_dir/'quality'/'independent_verification_report.json', {}) or {}
    sens = read_json(case_dir/'quality'/'sensitivity_report.json', {}) or {}
    maturity = read_json(case_dir/'quality'/'model_maturity_report.json', {}) or {}
    red = read_json(case_dir/'quality'/'red_team_review.json', {}) or {}
    for qid in question_ids(case_dir, question_id):
        sol=read_solution(case_dir,qid) or {}
        diag=sol.get('diagnostics',{}) or {}
        qfind=[]
        # Count candidates for this question.
        cand_count=0
        qtour=(tour.get('questions') or {}).get(qid) or {}
        cand_count=len(qtour.get('candidates') or [])
        mkey,mval=_metric(sol)
        # Generic high-gain signals.
        if isinstance(mval,(int,float)) and ('improvement' in (mkey or '') or 'gain' in (mkey or '')) and mval > 1.5 and cand_count < 3:
            qfind.append({'id':'SINGLE_SOLVER_HIGH_GAIN','severity':'P1','message':'结果相对 baseline 提升较大，但 solver 候选不足 3 个。','metric':mkey,'value':mval,'candidate_count':cand_count})
        if cand_count < 2:
            qfind.append({'id':'SINGLE_SOLVER_ONLY','severity':'P1','message':'当前问题没有真实 solver tournament；高置信结论应至少有 baseline + competition + verifier。','candidate_count':cand_count})
        if diag.get('sampling_based') and not (diag.get('convergence_check') or (sens.get('status') == 'passed')):
            qfind.append({'id':'NO_CONVERGENCE_FOR_SAMPLING','severity':'P1','message':'采样/仿真/射线追迹类结果缺少收敛性分析。'})
        if sol.get('quality_level') in {'evaluated_best','certified_optimal','global_optimal'} and indep.get('status') != 'passed':
            qfind.append({'id':'HIGH_CLAIM_WITHOUT_INDEPENDENT_RECOMPUTE','severity':'P1','message':'强质量声明缺少 independent-verify 通过证据。','quality_level':sol.get('quality_level')})
        if diag.get('constraint_margin') is not None:
            try:
                margin=float(diag.get('constraint_margin'))
                if margin < 0.05 and sens.get('status') != 'passed':
                    qfind.append({'id':'NEAR_ACTIVE_CONSTRAINT','severity':'P1','message':'约束安全裕度较小但缺少鲁棒性/敏感性分析。','constraint_margin':margin})
            except Exception:
                pass
        if maturity.get('status') == 'passed' and not diag.get('model_level') and not diag.get('model_maturity_artifact'):
            qfind.append({'id':'MODEL_MATURITY_WITHOUT_ARTIFACT','severity':'P2','message':'模型成熟度应链接具体 artifact，而不是只读声明。'})
        if red.get('status') == 'failed':
            qfind.append({'id':'RED_TEAM_BLOCKING_FINDINGS','severity':'P0','message':'Red Team 存在阻断问题。'})
        questions[qid]={'status':'failed' if any(f['severity']=='P0' for f in qfind) else ('warning' if qfind else 'passed'), 'findings':qfind}
        findings.extend([{'question_id':qid, **f} for f in qfind])
    status='failed' if any(f['severity']=='P0' for f in findings) else ('warning' if findings else 'passed')
    report={'gate':'optimism-risk-check','status':status,'findings':findings,'questions':questions,'generated_at':now_iso()}
    write_json(case_dir/'.agent'/'gate_reports'/'optimism_risk_check.json', report)
    return write_report(case_dir, 'optimism_risk_report.json', report)


def convergence_check(case_dir: Path, question_id: str | None = None) -> dict:
    case_dir=Path(case_dir).resolve(); ensure_quality_dirs(case_dir)
    warnings=[]; failures=[]; questions={}
    for qid in question_ids(case_dir, question_id):
        sol=read_solution(case_dir,qid) or {}
        diag=sol.get('diagnostics',{}) or {}
        conv=diag.get('convergence_check') or sol.get('convergence_check')
        if conv:
            status=conv.get('status','passed') if isinstance(conv,dict) else 'passed'
            questions[qid]={'status':status,'source':'solver_diagnostics','details':conv}
        elif diag.get('sampling_based') or diag.get('ray_tracing') or diag.get('monte_carlo'):
            warnings.append({'question_id':qid,'code':'MISSING_CONVERGENCE_CHECK','message':'采样/仿真/射线追迹问题必须提供收敛性分析。'})
            questions[qid]={'status':'warning','source':'missing'}
        else:
            questions[qid]={'status':'passed','source':'not_required','message':'未检测到采样/仿真类诊断字段。'}
    report={'gate':'convergence-check','status':'failed' if failures else ('warning' if warnings else 'passed'), 'questions':questions,'failures':failures,'warnings':warnings,'generated_at':now_iso()}
    write_json(case_dir/'.agent'/'gate_reports'/'convergence_check.json', report)
    return write_report(case_dir, 'convergence_check_report.json', report)


def baseline_protocol_check(case_dir: Path, question_id: str | None = None) -> dict:
    case_dir=Path(case_dir).resolve(); ensure_quality_dirs(case_dir)
    warnings=[]; questions={}
    for qid in question_ids(case_dir, question_id):
        sol=read_solution(case_dir,qid) or {}
        diag=sol.get('diagnostics',{}) or {}
        protocol=diag.get('comparison_protocol') or sol.get('comparison_protocol')
        if protocol:
            if isinstance(protocol, dict):
                ok=all(bool(protocol.get(k)) for k in ['same_metric_definition','same_sampling_strategy','same_domain_scope','same_weighting_policy'])
            else:
                ok=False
                protocol={'description': str(protocol), 'same_metric_definition': False, 'same_sampling_strategy': False, 'same_domain_scope': False, 'same_weighting_policy': False}
            questions[qid]={'status':'passed' if ok else 'warning','protocol':protocol}
            if not ok:
                warnings.append({'question_id':qid,'code':'COMPARISON_PROTOCOL_INCOMPLETE','protocol':protocol})
        elif any(k in str(sol).lower() for k in ['improvement','baseline','提升','比较','接收比']):
            warnings.append({'question_id':qid,'code':'MISSING_BASELINE_COMPARISON_PROTOCOL','message':'存在优化前后/基准对比结论，但未声明 same-protocol comparison。'})
            questions[qid]={'status':'warning'}
        else:
            questions[qid]={'status':'passed','source':'not_required'}
    report={'gate':'baseline-protocol-check','status':'warning' if warnings else 'passed','warnings':warnings,'questions':questions,'generated_at':now_iso()}
    write_json(case_dir/'.agent'/'gate_reports'/'baseline_protocol_check.json', report)
    return write_report(case_dir, 'baseline_protocol_check_report.json', report)


def optimism_debt_report(case_dir: Path, question_id: str | None = None) -> dict:
    case_dir=Path(case_dir).resolve(); ensure_quality_dirs(case_dir)
    risk=read_json(case_dir/'quality'/'optimism_risk_report.json', {}) or optimism_risk_check(case_dir, question_id)
    debts=[]
    for f in risk.get('findings',[]):
        debts.append({'id':f"{f.get('question_id')}-{f.get('id')}", 'severity':f.get('severity'), 'description':f.get('message'), 'required_to_clear_for_final': f.get('severity') in {'P0','P1'}, 'status':'open'})
    final_allowed=not any(d['required_to_clear_for_final'] and d['status']=='open' for d in debts)
    report={'gate':'optimism-debt-report','status':'warning' if debts else 'passed','final_allowed':final_allowed,'debts':debts,'generated_at':now_iso()}
    write_json(case_dir/'quality'/'optimism_debt_ledger.json', report)
    md=['# Optimism Debt Ledger','',f"- status: `{report['status']}`",f"- final_allowed: `{final_allowed}`",'', '| id | severity | required for final | description |','|---|---:|---:|---|']
    for d in debts:
        md.append(f"| {d['id']} | {d['severity']} | {d['required_to_clear_for_final']} | {d['description']} |")
    (case_dir/'quality'/'optimism_debt_ledger.md').write_text('\n'.join(md)+'\n', encoding='utf-8')
    return report
