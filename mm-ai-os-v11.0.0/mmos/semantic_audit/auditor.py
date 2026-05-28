from __future__ import annotations
from pathlib import Path
import re
from typing import Any
from mmos.kernel.jsonio import read_json, write_json

SEMANTIC_CATEGORIES = [
    'task_semantics','decision_variable_semantics','objective_semantics','constraint_semantics',
    'temporal_semantics','spatial_geometry_semantics','unit_dimension_semantics','data_attachment_semantics',
    'question_dependency_semantics','scenario_semantics','statistical_semantics','optimization_semantics',
    'physical_mechanism_semantics','output_semantics','paper_semantics'
]

KEYWORDS = {
    'optimization': r'最优|最大|最小|优化|规划|目标|决策|方案|控制|调整',
    'prediction': r'预测|预报|回归|外推|时间序列|训练|测试',
    'evaluation': r'评价|评估|指标|权重|排序|综合',
    'simulation': r'仿真|模拟|数值|蒙特卡洛|采样|随机',
    'physics': r'压力|温度|密度|速度|流量|弹性模量|热|力|能量|质量守恒|微分|边界|几何|角速度',
    'statistics': r'置信|显著|样本|总体|概率|方差|检验|分布',
}

UNIT_PATTERNS = [
    r'\bms\b', r'\bs\b', r'\bmin\b', r'MPa', r'Pa', r'mm', r'cm', r'm', r'rad/s', r'rad/ms', r'mg/mm3', r'mm3/ms', r'°C|℃'
]


def _read_graph(case_dir: Path) -> dict[str, Any]:
    return read_json(case_dir / 'workspace' / 'problem_graph.json', {}) or read_json(case_dir / 'registry' / 'questions_registry.json', {}) or {'questions': []}


def _corpus_text(case_dir: Path) -> str:
    p = case_dir / 'workspace' / 'problem_corpus.md'
    return p.read_text(encoding='utf-8', errors='ignore') if p.exists() else ''


def _question_text(q: dict[str, Any], corpus: str) -> str:
    txt = q.get('source_excerpt') or ''
    if len(txt) >= 50:
        return txt
    span = q.get('source_span') or {}
    try:
        s, e = int(span.get('start', 0)), int(span.get('end', 0))
        if e > s:
            return corpus[s:e]
    except Exception:
        pass
    return txt or corpus[:3000]


def _detect_task_types(text: str) -> list[str]:
    found = []
    if re.search(KEYWORDS['optimization'], text): found.append('optimization_or_control')
    if re.search(KEYWORDS['prediction'], text): found.append('prediction_or_forecasting')
    if re.search(KEYWORDS['evaluation'], text): found.append('evaluation_or_decision')
    if re.search(KEYWORDS['simulation'], text): found.append('simulation_or_numerical_modeling')
    if re.search(KEYWORDS['physics'], text): found.append('mechanistic_or_physical_modeling')
    if re.search(KEYWORDS['statistics'], text): found.append('statistical_inference')
    return found or ['open_ended_modeling']


def _extract_units(text: str) -> list[str]:
    out = []
    for pat in UNIT_PATTERNS:
        if re.search(pat, text, flags=re.I):
            out.append(pat.replace('\\b',''))
    return sorted(set(out))


def _risk(rid: str, severity: str, category: str, description: str, evidence: str = '') -> dict[str, Any]:
    return {'risk_id': rid, 'severity': severity, 'category': category, 'description': description, 'required_evidence': evidence}


def _audit_question(q: dict[str, Any], idx: int, corpus: str, files: list[Path]) -> dict[str, Any]:
    qid = q.get('question_id') or f'Q{idx+1}'
    text = _question_text(q, corpus)
    task_types = _detect_task_types(text)
    risks: list[dict[str, Any]] = []

    # Task semantics
    if 'optimization_or_control' in task_types and not re.search(r'变量|决策|控制|设置|调整|取值|速度|温度|时长|角速度|位置|参数', text):
        risks.append(_risk(f'{qid}-TASK-001', 'P1', 'task_semantics', 'Optimization/control intent exists but decision variables are not explicit.', f'contracts/questions/{qid}/variable_registry.json'))

    # Decision variables
    decision_cues = re.findall(r'(?:确定|设置|调整|选择|给出|优化)([^。；;\n]{0,60})', text)

    # Objective semantics
    objective_terms = []
    for term in ['稳定','最小','最大','尽可能','误差','波动','面积','成本','收益','风险','公平','准确率']:
        if term in text:
            objective_terms.append(term)
    if objective_terms and not re.search(r'目标函数|指标|度量|RMS|方差|积分|偏差|损失|score|objective', text, flags=re.I):
        risks.append(_risk(f'{qid}-OBJ-001', 'P2', 'objective_semantics', 'Natural-language objective requires mathematical metric definition.', f'workspace/claim_evidence/{qid}.claims.json'))

    # Constraint semantics
    hard_constraints = []
    if re.search(r'范围|不超过|不小于|至少|至多|必须|要求|约束|关闭|开启后|保持一致|满足', text):
        hard_constraints.append('explicit_constraint_language_detected')
    if hard_constraints and not q.get('extracted_requirements', {}).get('has_constraints', False):
        risks.append(_risk(f'{qid}-CON-001', 'P1', 'constraint_semantics', 'Constraint language detected but parser did not mark constraints.', f'contracts/questions/{qid}/constraint_registry.json'))

    # Temporal semantics
    temporal_terms = re.findall(r'\d+(?:\.\d+)?\s*(?:ms|s|min|秒|分钟|小时|次/秒|每秒|周期|间隔|时长)', text, flags=re.I)
    if temporal_terms and re.search(r'周期|每秒|关闭|开启|间隔|相差|采样|稳定', text):
        risks.append(_risk(f'{qid}-TIME-001', 'P1', 'temporal_semantics', 'Temporal/event semantics must be represented explicitly; do not replace by average duty cycle unless justified.', f'results/{qid}/event_timing_report.json'))

    # Spatial / geometry semantics
    if re.search(r'坐标|角度|半径|直径|长度|面积|体积|中点|端点|方向|圆|圆锥|曲线|边缘', text):
        risks.append(_risk(f'{qid}-GEO-001', 'P2', 'spatial_geometry_semantics', 'Geometry/coordinate semantics detected; require geometry contract and unit normalization.', f'contracts/questions/{qid}/geometry_contract.json'))

    # Unit semantics
    units = _extract_units(text)
    if len(units) >= 2:
        risks.append(_risk(f'{qid}-UNIT-001', 'P1', 'unit_dimension_semantics', 'Multiple units detected; require unit normalization and dimension consistency evidence.', f'results/{qid}/unit_consistency.json'))

    # Attachment semantics
    attachment_refs = re.findall(r'附件\s*\d+', text)
    if attachment_refs or files:
        risks.append(_risk(f'{qid}-DATA-001', 'P1', 'data_attachment_semantics', 'Attachments/data must have semantic roles and be linked to model equations or outputs.', 'workspace/semantic_audit/attachment_semantics.json'))

    # Dependencies
    if re.search(r'在问题\s*\d+|基于问题|结合问题|上一问|前一问', text):
        risks.append(_risk(f'{qid}-DEP-001', 'P1', 'question_dependency_semantics', 'Question dependency detected; downstream model must inherit upstream definitions consistently.', 'workspace/problem/question_dependency_graph.json'))

    # Scenario semantics
    if re.search(r'情况下|基础上|增加|安装|不同|分别|方案|策略|工况|场景', text):
        risks.append(_risk(f'{qid}-SCEN-001', 'P2', 'scenario_semantics', 'Multiple scenarios/strategies detected; each scenario must have separate result and comparison.', f'results/{qid}/scenario_comparison.json'))

    # Statistics
    if re.search(KEYWORDS['statistics'], text):
        risks.append(_risk(f'{qid}-STAT-001', 'P1', 'statistical_semantics', 'Statistical task requires uncertainty, leakage and validation semantics.', f'results/{qid}/statistical_validation.json'))

    # Optimization
    if 'optimization_or_control' in task_types:
        risks.append(_risk(f'{qid}-OPT-001', 'P1', 'optimization_semantics', 'Optimization/control task requires variables, objective, constraints, feasibility and search evidence.', f'results/{qid}/optimization_trace.csv'))

    # Physics
    if 'mechanistic_or_physical_modeling' in task_types:
        risks.append(_risk(f'{qid}-PHY-001', 'P1', 'physical_mechanism_semantics', 'Mechanistic model requires invariants/boundary conditions and independent physical checks.', f'results/{qid}/physical_invariants.json'))

    # Output semantics
    if re.search(r'result\.(csv|xlsx)|存放|保存|输出|列出|画出|给出.*指标|提交', text, flags=re.I):
        risks.append(_risk(f'{qid}-OUT-001', 'P1', 'output_semantics', 'Explicit output requirement detected; output registry must link file/schema to this question.', 'registry/outputs_registry.json'))

    # Paper semantics
    risks.append(_risk(f'{qid}-PAPER-001', 'P2', 'paper_semantics', 'Paper must include problem goal, model choice, formula chain, result table/figure, validation and limitations for this question.', f'paper/sections/{qid}.md'))

    categories = {cat: {'status': 'covered', 'risks': [r for r in risks if r['category'] == cat]} for cat in SEMANTIC_CATEGORIES}
    return {
        'question_id': qid,
        'status': 'warning' if risks else 'passed',
        'task_types': task_types,
        'detected_units': units,
        'decision_cues': decision_cues[:8],
        'categories': categories,
        'risks': risks,
        'risk_count': len(risks),
        'critical_risk_count': sum(1 for r in risks if r['severity'] == 'P0'),
        'high_risk_count': sum(1 for r in risks if r['severity'] == 'P1'),
    }


def semantic_audit(case_dir: Path, question_id: str | None = None, strict: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    graph = _read_graph(case_dir)
    corpus = _corpus_text(case_dir)
    raw_dir = case_dir / 'data' / 'raw'
    files = list(raw_dir.glob('*')) if raw_dir.exists() else []
    questions = graph.get('questions', []) or []
    if question_id:
        questions = [q for q in questions if q.get('question_id') == question_id]
    if not questions:
        questions = [{'question_id': 'Q1', 'source_excerpt': corpus[:3000], 'extracted_requirements': {}}]
    q_reports = [_audit_question(q, i, corpus, files) for i, q in enumerate(questions)]
    all_risks = [r for qr in q_reports for r in qr.get('risks', [])]
    # Strict audit does not fail merely because risks exist; it fails if required structural files are absent.
    missing_structural = []
    if not graph.get('questions'):
        missing_structural.append('problem_graph.questions')
    if files and not (case_dir / 'data' / 'manifest' / 'data_manifest.json').exists():
        missing_structural.append('data_manifest')
    status = 'failed' if strict and missing_structural else ('warning' if all_risks else 'passed')
    case_graph = {
        'case_id': case_dir.name,
        'semantic_categories': SEMANTIC_CATEGORIES,
        'questions': [{'question_id': qr['question_id'], 'task_types': qr['task_types'], 'risk_count': qr['risk_count']} for qr in q_reports],
        'attachment_count': len(files),
        'risk_count': len(all_risks),
    }
    out_dir = case_dir / 'workspace' / 'semantic_audit'
    for qr in q_reports:
        write_json(out_dir / f"{qr['question_id']}.semantic_contract.json", qr)
    risk_register = {'case_id': case_dir.name, 'risks': all_risks, 'risk_count': len(all_risks)}
    write_json(out_dir / 'case_semantic_graph.json', case_graph)
    write_json(out_dir / 'semantic_risk_register.json', risk_register)
    md = ['# Semantic Audit Report', '', f'- case_id: `{case_dir.name}`', f'- status: `{status}`', f'- risk_count: `{len(all_risks)}`', '', '| question | task types | risk count | high risks |', '|---|---|---:|---:|']
    for qr in q_reports:
        md.append(f"| {qr['question_id']} | {', '.join(qr['task_types'])} | {qr['risk_count']} | {qr['high_risk_count']} |")
    md.append('\n## Risk Register\n')
    for r in all_risks[:200]:
        md.append(f"- **{r['severity']} {r['risk_id']}** [{r['category']}] {r['description']} Evidence: `{r.get('required_evidence','')}`")
    (out_dir / 'semantic_audit_report.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    result = {'status': status, 'case_id': case_dir.name, 'question_count': len(q_reports), 'semantic_categories': SEMANTIC_CATEGORIES, 'missing_structural': missing_structural, 'risk_count': len(all_risks), 'high_risk_count': sum(1 for r in all_risks if r['severity'] == 'P1'), 'outputs': {'case_semantic_graph': str(out_dir / 'case_semantic_graph.json'), 'risk_register': str(out_dir / 'semantic_risk_register.json'), 'report': str(out_dir / 'semantic_audit_report.md')}}
    write_json(case_dir / 'quality' / 'semantic_audit.json', result)
    return result
