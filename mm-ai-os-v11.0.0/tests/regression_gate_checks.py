#!/usr/bin/env python3
from __future__ import annotations
import json, os
import shutil
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mmos.kernel.paths import OSPaths
from mmos.contracts.manager import ensure_case_scaffold, activate_question, check_contracts
from mmos.ingestion.document_ingestor import build_problem_corpus
from mmos.problem_graph.parser import build_problem_graph
from mmos.artifacts.outputs import validate_outputs, discover_outputs
from mmos.artifacts.package import package_case, register_output_draft, output_build
from mmos.gates.report_consistency import report_consistency_check
from mmos.gates.final_gate import final_gate_check
from mmos.gates.solver_verify import verify_solver_result
from mmos.workflow_runtime.runtime import run_stage, run_case_flow
from mmos.agent_protocols.tasks import generate_agent_tasks, agent_protocol_check
from mmos.agent_protocols.parse_review import create_parse_review, apply_parse_review
from mmos.agent_protocols.verifiers import scaffold_verifier, run_verifiers, compare_verifiers
from mmos.agent_protocols.paper import paper_build, paper_quality_check


def reset_case(case_id: str) -> Path:
    case = ROOT / 'cases' / case_id
    shutil.rmtree(case, ignore_errors=True)
    ensure_case_scaffold(case)
    return case


def main():
    # 1) Path traversal must be rejected by the resolver.
    try:
        OSPaths(ROOT).case_dir('../mmos_escape')
    except ValueError as exc:
        assert 'invalid case id' in str(exc)
    else:
        raise AssertionError('path traversal case id was accepted')
    assert not (ROOT.parent / 'mmos_escape').exists()

    # 2) Empty output registries and package attempts must fail.
    case = reset_case('fixture_empty_gate')
    out = validate_outputs(case)
    assert out['status'] == 'failed', out
    assert any(f['code'] == 'EMPTY_OUTPUT_REGISTRY' for f in out['failures']), out
    pkg = package_case(case)
    assert pkg['status'] == 'failed' and pkg['code'] == 'FINAL_GATE_NOT_PASSED', pkg

    # 3) Default contracts must not pass as refined competition contracts.
    case = reset_case('fixture_contract_gate')
    (case/'data/raw/problem.md').write_text('问题一：建立优化模型，输出结果。\n', encoding='utf-8')
    build_problem_corpus(case)
    build_problem_graph(case)
    activate_question(case, 'Q1', qtype='auto')
    cc = check_contracts(case, 'Q1')
    assert cc['status'] == 'failed', cc
    codes = {f['code'] for f in cc['failures']}
    assert 'VARIABLE_REGISTRY_NOT_REFINED' in codes, cc
    assert 'VALIDATION_CONTRACT_GENERIC_ONLY' in codes, cc

    # 4) Report numeric claims must be field-bound.
    case = reset_case('fixture_report_gate')
    (case/'results/Q1/outputs').mkdir(parents=True, exist_ok=True)
    (case/'reports').mkdir(parents=True, exist_ok=True)
    (case/'registry/questions_registry.json').write_text(json.dumps({
        'case_id':'fixture_report_gate',
        'questions':[{'question_id':'Q1','required':True,'status':'activated','type':'generic_optimization'}]
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    (case/'results/Q1/outputs/solution_real.json').write_text(json.dumps({
        'question_id':'Q1','status':'success','stage':'real','quality_level':'heuristic_feasible',
        'objective_value':123.0,'diagnostics':{'constraints_checked':True,'fallback_used':False}
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    (case/'reports/Q1_report.md').write_text('# Q1 Report\n\nThe final objective value is 999999 and intentionally conflicts with the structured result.\n', encoding='utf-8')
    rc = report_consistency_check(case, report_path='reports/Q1_report.md')
    assert rc['status'] == 'failed', rc
    assert any(f['code'] == 'SOLUTION_NUMBER_NOT_REPORTED' for f in rc['failures']), rc


    # 5) A report that contains both the correct value and a stale conflicting value must fail.
    (case/'reports/Q1_report.md').write_text(
        '# Q1 Report\n\nobjective_value: 123.0\nA stale table later says objective_value: 999999.\n',
        encoding='utf-8'
    )
    rc2 = report_consistency_check(case, report_path='reports/Q1_report.md')
    assert rc2['status'] == 'failed', rc2
    assert any(f['code'] == 'FIELD_NUMERIC_CONFLICT' for f in rc2['failures']), rc2

    # 6) Every required question must own at least one required registered output.
    case = reset_case('fixture_missing_question_output')
    (case/'registry/questions_registry.json').write_text(json.dumps({
        'case_id':'fixture_missing_question_output',
        'questions':[{'question_id':'Q1','required':True,'status':'activated'}, {'question_id':'Q2','required':True,'status':'activated'}]
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    for qid, obj in [('Q1', 1.0), ('Q2', 2.0)]:
        (case/f'results/{qid}/outputs').mkdir(parents=True, exist_ok=True)
        (case/f'results/{qid}/outputs/solution_real.json').write_text(json.dumps({
            'question_id':qid,'status':'success','stage':'real','quality_level':'local_optimal',
            'objective_value':obj,'diagnostics':{'constraints_checked':True,'fallback_used':False}
        }, ensure_ascii=False, indent=2), encoding='utf-8')
    (case/'reports/Q1_report.md').write_text('# Q1 Report\n\nobjective_value: 1.0\n', encoding='utf-8')
    (case/'reports/Q2_report.md').write_text('# Q2 Report\n\nobjective_value: 2.0\n', encoding='utf-8')
    (case/'registry/outputs_registry.json').write_text(json.dumps({
        'case_id':'fixture_missing_question_output',
        'outputs':[{'path':'results/Q1/outputs/solution_real.json','type':'json','required':True,'owner_question':'Q1','validator':{'required_non_empty':True}}]
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    # Mark optional quality gates passed to isolate the missing-output invariant.
    for rel, gate in [
        ('model_maturity_report.json','model-maturity-check'),('bound_check_report.json','bound-check'),
        ('solver_tournament_report.json','solver-tournament'),('independent_verification_report.json','independent-verify'),
        ('sensitivity_report.json','sensitivity-analysis'),('red_team_review.json','red-team-review'),
        ('convergence_check_report.json','convergence-check'),('baseline_protocol_check_report.json','baseline-protocol-check'),
        ('optimism_risk_report.json','optimism-risk-check'),('optimism_debt_ledger.json','optimism-debt-report'),
        ('solution_improvement_report.json','solution-improve'),('surrogate_quality_report.json','quality-oracle-v2')]:
        data={'gate':gate,'status':'passed'}
        if gate == 'optimism-debt-report':
            data['final_allowed'] = True
        (case/'quality'/rel).parent.mkdir(parents=True, exist_ok=True)
        (case/'quality'/rel).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    fg = final_gate_check(case, strict_warnings=False)
    assert fg['status'] == 'failed', fg
    assert any(f['code'] == 'NO_REQUIRED_OUTPUT_FOR_QUESTION' and f.get('question_id') == 'Q2' for f in fg['failures']), fg

    # 7) --resume must not reuse a checkpoint after raw data changes.
    case = reset_case('fixture_resume_data_hash')
    (case/'registry/questions_registry.json').write_text(json.dumps({'case_id':'fixture_resume_data_hash','questions':[{'question_id':'Q1','required':True,'status':'activated'}]}, ensure_ascii=False, indent=2), encoding='utf-8')
    qdir = case/'engineering/questions/Q1'
    qdir.mkdir(parents=True, exist_ok=True)
    for name in ['validate.py', 'model.py', 'report.py']:
        (qdir/name).write_text('def validate_inputs(context): return {"status":"passed"}\n' if name == 'validate.py' else ('def build_model(context): return {"status":"ok"}\n' if name == 'model.py' else 'def render_report(result): return "# Q1 Report\\n\\nobjective_value: %s\\n" % result.get("objective_value")\n'), encoding='utf-8')
    (qdir/'solve.py').write_text('def solve(stage,budget,context): return {"question_id":"Q1","status":"success","stage":stage,"quality_level":"local_optimal","objective_value":1.0,"diagnostics":{"constraints_checked":True}}\n', encoding='utf-8')
    (qdir/'run.py').write_text((ROOT/'templates/question_engineering/run.py').read_text(encoding='utf-8'), encoding='utf-8')
    (case/'data/raw').mkdir(parents=True, exist_ok=True)
    (case/'data/raw/input.csv').write_text('x\n1\n', encoding='utf-8')
    first = run_stage(case, 'Q1', 'validate', budget='fast')
    assert first['status'] == 'passed', first
    (case/'data/raw/input.csv').write_text('x\n999\n', encoding='utf-8')
    resumed = run_case_flow(case, budget='fast', resume=True)
    assert resumed['status'] == 'passed', resumed
    assert not resumed['results'][0].get('skipped_by_resume'), resumed

    # 8) strict solver schema must have observable behavior.
    loose = case/'results/Q1/outputs/loose.json'
    loose.parent.mkdir(parents=True, exist_ok=True)
    loose.write_text(json.dumps({'question_id':'Q1','status':'success','quality_level':'local_optimal','objective_value':1.0,'diagnostics':{'constraints_checked':True},'unexpected_extra':1}, ensure_ascii=False, indent=2), encoding='utf-8')
    strict = verify_solver_result(loose, strict_schema=True)
    assert strict['status'] == 'failed', strict
    assert any(f['code'] == 'STRICT_SCHEMA_UNEXPECTED_FIELDS' for f in strict['failures']), strict



    # 9) Structured validation contract entries must count as refined validators.
    case = reset_case('fixture_structured_validator_contract')
    (case/'data/raw/problem.md').write_text('问题一：建立优化模型，输出结果。\n', encoding='utf-8')
    build_problem_corpus(case); build_problem_graph(case); activate_question(case, 'Q1', qtype='auto')
    qd = case/'contracts/questions/Q1'
    (qd/'variable_registry.json').write_text(json.dumps({'variables':[{'name':'x','role':'decision'}]}, ensure_ascii=False, indent=2), encoding='utf-8')
    (qd/'constraint_registry.json').write_text(json.dumps({'constraints':[{'name':'c1','expression':'x>=0'}]}, ensure_ascii=False, indent=2), encoding='utf-8')
    (qd/'validation_contract.json').write_text(json.dumps({'validators':[{'name':'domain_recompute_check','tolerance':1e-9}]}, ensure_ascii=False, indent=2), encoding='utf-8')
    (qd/'output_contract.json').write_text(json.dumps({'outputs':[{'path':'results/Q1/outputs/solution_real.json','type':'json','required':True}]}, ensure_ascii=False, indent=2), encoding='utf-8')
    cc2 = check_contracts(case, 'Q1')
    assert cc2['status'] == 'passed', cc2

    # 10) Final gate must recompute contract-check and must not trust forged quality JSON.
    case = reset_case('fixture_contract_final_gate')
    (case/'registry/questions_registry.json').write_text(json.dumps({'case_id':case.name,'questions':[{'question_id':'Q1','required':True,'status':'activated'}]}, ensure_ascii=False, indent=2), encoding='utf-8')
    qd = case/'contracts/questions/Q1'; qd.mkdir(parents=True, exist_ok=True)
    # Build default placeholder contracts, then create otherwise-valid outputs and forged pass quality reports.
    activate_question(case, 'Q1', qtype='auto')
    (case/'results/Q1/outputs').mkdir(parents=True, exist_ok=True)
    (case/'results/Q1/outputs/solution_real.json').write_text(json.dumps({'question_id':'Q1','status':'success','stage':'real','quality_level':'local_optimal','objective_value':7.0,'metrics':{'row_count':1},'diagnostics':{'constraints_checked':True,'fallback_used':False,'model_level':'L4','multi_solver':True,'sensitivity_parameters':['x']}}, ensure_ascii=False, indent=2), encoding='utf-8')
    (case/'results/Q1/outputs/solution_reduced.json').write_text(json.dumps({'question_id':'Q1','status':'success','stage':'reduced','quality_level':'local_optimal','objective_value':7.0,'metrics':{'row_count':1},'diagnostics':{'constraints_checked':True}}, ensure_ascii=False, indent=2), encoding='utf-8')
    (case/'reports/Q1_report.md').write_text('# Q1 Report\n\nobjective_value: 7.0\nmetrics.row_count: 1\nThis report is long enough to pass minimum text checks and bind the numeric value.\n', encoding='utf-8')
    (case/'registry/outputs_registry.json').write_text(json.dumps({'case_id':case.name,'outputs':[{'path':'results/Q1/outputs/solution_real.json','type':'json','required':True,'owner_question':'Q1','validator':{'required_non_empty':True}}]}, ensure_ascii=False, indent=2), encoding='utf-8')
    for rel, gate in [('model_maturity_report.json','model-maturity-check'),('bound_check_report.json','bound-check'),('solver_tournament_report.json','solver-tournament'),('independent_verification_report.json','independent-verify'),('sensitivity_report.json','sensitivity-analysis'),('red_team_review.json','red-team-review'),('convergence_check_report.json','convergence-check'),('baseline_protocol_check_report.json','baseline-protocol-check'),('optimism_risk_report.json','optimism-risk-check'),('optimism_debt_ledger.json','optimism-debt-report'),('solution_improvement_report.json','solution-improve'),('surrogate_quality_report.json','quality-oracle-v2')]:
        data={'gate':gate,'status':'passed'}
        if gate == 'optimism-debt-report': data['final_allowed'] = True
        (case/'quality'/rel).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    fg2 = final_gate_check(case, strict_warnings=False)
    assert fg2['status'] == 'failed', fg2
    assert any(f['code'] == 'CONTRACT_CHECK_NOT_PASSED' for f in fg2['failures']), fg2

    # 11) output-discover/output-build must be idempotent after submitted copies exist.
    case = reset_case('fixture_output_build_idempotent')
    (case/'results/Q1/outputs').mkdir(parents=True, exist_ok=True)
    (case/'results/Q1/outputs/result.csv').write_text('a,b\n1,2\n', encoding='utf-8')
    d1 = discover_outputs(case, write_draft=True)
    assert len(d1['outputs']) == 1, d1
    assert register_output_draft(case)['status'] == 'ok'
    b1 = output_build(case)
    assert b1['status'] == 'ok', b1
    d2 = discover_outputs(case, write_draft=True)
    assert len(d2['outputs']) == 1, d2
    assert register_output_draft(case)['status'] == 'ok'
    b2 = output_build(case)
    assert b2['status'] == 'ok', b2

    # 12) CLI must return non-zero when a command emits JSON status=failed.
    proc = subprocess.run([sys.executable, str(ROOT/'scripts/mmtool.py'), 'output-validate', 'fixture_empty_gate'], cwd=str(ROOT), text=True, capture_output=True)
    assert proc.returncode != 0, proc.stdout

    # 13) Agent protocol layer must generate task cards, parse-review artifacts, verifier plugins, and paper-quality gates.
    case = reset_case('fixture_agent_protocol_layer')
    (case/'data/raw/problem.md').write_text('问题一：统计分析并输出指标。\n问题二：建立优化模型并输出方案。\n', encoding='utf-8')
    build_problem_corpus(case); graph = build_problem_graph(case)
    assert len(graph.get('questions', [])) >= 2, graph
    for qid in ['Q1','Q2']:
        activate_question(case, qid, qtype='auto')
    task = generate_agent_tasks(case, phase='all', force=True)
    assert task['status'] == 'ok' and any('Q1_modeling_protocol.md' in c for c in task['cards']), task
    ap = agent_protocol_check(case, strict=True)
    assert ap['status'] == 'passed', ap
    cr = create_parse_review(case)
    assert cr['status'] == 'warning', cr
    template = json.loads((case/'workspace/problem_graph.review_template.json').read_text(encoding='utf-8'))
    template['status'] = 'passed'
    (case/'workspace/problem_graph.agent_review.json').write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding='utf-8')
    ar = apply_parse_review(case)
    assert ar['status'] == 'passed' and (case/'workspace/problem_graph.final.json').exists(), ar

    # 14) Verifier plugins must provide a real independent-artifact pathway.
    (case/'results/Q1/outputs').mkdir(parents=True, exist_ok=True)
    for name in ['solution_real.json','solution_reduced.json']:
        (case/f'results/Q1/outputs/{name}').write_text(json.dumps({'question_id':'Q1','status':'success','stage':'real','quality_level':'local_optimal','objective_value':5.0,'diagnostics':{'constraints_checked':True}}, ensure_ascii=False, indent=2), encoding='utf-8')
    vs = scaffold_verifier(case, 'Q1', force=True)
    assert vs['status'] == 'ok', vs
    vr = run_verifiers(case, 'Q1')
    assert vr['status'] == 'passed', vr
    vc = compare_verifiers(case, 'Q1', strict=True)
    assert vc['status'] == 'passed', vc

    # 15) Paper build creates a contest-paper scaffold; strict quality gate catches draft text and passes after cleanup.
    (case/'reports/Q1_report.md').write_text('# Q1 Report\n\nobjective_value: 5.0\n', encoding='utf-8')
    pb = paper_build(case, force=True)
    assert pb['status'] == 'ok' and (case/'paper/main_paper.md').exists(), pb
    pq_draft = paper_quality_check(case, strict=True)
    assert pq_draft['status'] == 'failed', pq_draft
    clean = '''# 数学建模竞赛论文

## 摘要
Q1 objective_value 为 5.0，Q2 给出优化建模框架。

## 问题重述
Q1 和 Q2 均被覆盖。

## 模型假设
输入数据已完成审计，变量单位一致。

## 符号说明
| 符号 | 含义 |
|---|---|
| x | 决策变量 |

## 模型建立
Q1 采用统计指标模型，Q2 采用约束优化模型。

## 求解方法
使用可复现 Python solver 输出结构化结果。

## 结果分析
Q1 objective_value: 5.0。

## 模型检验
独立 verifier 已复算 Q1 核心指标。

## 灵敏度分析
对关键参数进行扰动分析。

## 模型优缺点
模型可追溯，但仍需在真实赛题中补充领域假设。

## 参考文献
[1] Contest data and official problem statement.
'''
    (case/'paper/main_paper.md').write_text(clean, encoding='utf-8')
    (case/'paper/figures').mkdir(parents=True, exist_ok=True)
    (case/'paper/figures/q1.png').write_text('placeholder image artifact for manifest test', encoding='utf-8')
    (case/'engineering/questions/Q1/figures').mkdir(parents=True, exist_ok=True)
    (case/'engineering/questions/Q1/figures/plot_q1.py').write_text('print("plot")\n', encoding='utf-8')
    (case/'paper/figures_manifest.json').write_text(json.dumps({'figures':[{'path':'paper/figures/q1.png','title':'Q1 result','source_script':'engineering/questions/Q1/figures/plot_q1.py','cited_in_section':'结果分析'}]}, ensure_ascii=False, indent=2), encoding='utf-8')
    pq = paper_quality_check(case, strict=True)
    assert pq['status'] == 'passed', pq

    print('regression_gate_checks passed', flush=True); os._exit(0)


if __name__ == '__main__':
    main()
