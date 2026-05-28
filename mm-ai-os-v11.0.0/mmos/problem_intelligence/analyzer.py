from __future__ import annotations
from pathlib import Path
from typing import Any
import re
from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from mmos.quality_oracle.common import registry_questions


def _load_corpus(case_dir: Path) -> str:
    for rel in ['workspace/problem_corpus.md', 'data/raw/problem.md', 'data/raw/problem.txt']:
        p = case_dir / rel
        if p.exists():
            return p.read_text(encoding='utf-8', errors='ignore')
    return ''


def _signals(text: str) -> dict[str, bool]:
    low = text.lower()
    return {
        'optimization': any(k in text for k in ['优化', '最大', '最小', '规划', '目标函数']) or 'optimiz' in low,
        'prediction': any(k in text for k in ['预测', ' forecast', '回归', '时间序列']) or 'predict' in low,
        'statistics': any(k in text for k in ['统计', '评价', '指标', '显著', '相关']) or 'statistic' in low,
        'simulation': any(k in text for k in ['仿真', '模拟', '随机', '蒙特卡洛']) or 'simulation' in low,
        'robustness': any(k in text for k in ['灵敏度', '鲁棒', '稳定', '敏感性']) or 'sensitivity' in low,
        'figures_expected': any(k in text for k in ['图', '可视化', '分布', '曲线', '趋势']) or 'plot' in low,
    }


def problem_intelligence(case_dir: Path, target: str = 'first_prize') -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    out_dir = case_dir / 'workspace' / 'problem_intelligence'
    out_dir.mkdir(parents=True, exist_ok=True)
    graph = read_json(case_dir / 'workspace' / 'problem_graph.final.json', {}) or read_json(case_dir / 'workspace' / 'problem_graph.json', {}) or {}
    qs = registry_questions(case_dir)
    text = _load_corpus(case_dir)
    signals = _signals(text)
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if not qs:
        failures.append({'code': 'NO_REQUIRED_QUESTIONS', 'message': 'Run problem-parse-v2/question-activate first.'})
    if not text.strip():
        warnings.append({'code': 'EMPTY_OR_MISSING_PROBLEM_CORPUS'})

    hidden = []
    if signals['optimization']:
        hidden.append({'type': 'constraint_feasibility', 'requirement': '所有优化结果必须显式复核约束可行性和边界。'})
    if signals['prediction']:
        hidden.append({'type': 'validation_split', 'requirement': '预测模型必须给出 holdout/cross-validation 或泄漏检查。'})
    if signals['simulation']:
        hidden.append({'type': 'random_seed_convergence', 'requirement': '仿真模型必须给出收敛、随机种子和置信区间。'})
    if signals['robustness'] or len(qs) >= 4:
        hidden.append({'type': 'robustness_analysis', 'requirement': '高奖论文必须包含关键参数扰动和敏感性图。'})
    if not hidden:
        hidden.append({'type': 'baseline_and_verification', 'requirement': '每问至少需要 baseline、advanced model 和独立验证证据。'})

    scoring_points = []
    for q in qs:
        qid = q.get('question_id') or q.get('id')
        title = q.get('title') or q.get('source_excerpt', '')[:80]
        scoring_points.append({
            'question_id': qid,
            'likely_scoring_points': [
                '题意覆盖完整', '模型变量/目标/约束清晰', '求解结果可复现',
                '独立验证或对照模型', '论文中有清晰表格/图形解释'
            ],
            'title': title,
        })
    traps = []
    if re.search(r'单位|km|m|kg|小时|分钟|元|万元|%', text, re.I):
        traps.append({'code': 'UNIT_CONVERSION_RISK', 'description': '题面存在单位信号，contract 和 verifier 应检查单位一致性。'})
    if len(qs) > 1:
        traps.append({'code': 'CROSS_QUESTION_DEPENDENCY_RISK', 'description': '多小问可能存在结果传递，paper 和 solver 需要说明依赖关系。'})
    if not traps:
        traps.append({'code': 'GENERIC_MODELING_RISK', 'description': '避免只用通用模板，应结合题面数据和领域路由生成高级模型。'})

    dependency_graph = {'nodes': [], 'edges': []}
    last_qid = None
    for q in qs:
        qid = q.get('question_id') or q.get('id')
        dependency_graph['nodes'].append({'id': qid, 'title': q.get('title')})
        if last_qid:
            dependency_graph['edges'].append({'from': last_qid, 'to': qid, 'type': 'possible_downstream_dependency', 'confidence': 'medium'})
        last_qid = qid

    data_need_map = {q.get('question_id') or q.get('id'): ['data/raw/*', 'data/manifest/data_manifest.json', 'contract variable/objective/constraint registries'] for q in qs}
    output_need_map = {q.get('question_id') or q.get('id'): ['solution_real.json', 'registered output file', 'paper section', 'verifier report'] for q in qs}
    judge_expectation = [
        '评委通常优先看：问题覆盖、模型合理性、结果可信度、论文表达、创新亮点。',
        '高奖解法应避免单一弱启发式；至少展示 baseline vs advanced 对比和独立复核。',
    ]
    artifacts = {
        'hidden_requirements': hidden,
        'scoring_points': scoring_points,
        'trap_analysis': traps,
        'dependency_graph': dependency_graph,
        'data_need_map': data_need_map,
        'output_need_map': output_need_map,
        'judge_expectation': judge_expectation,
    }
    write_json(out_dir / 'hidden_requirements.json', {'status': 'passed', 'items': hidden, 'generated_at': now_iso()})
    write_json(out_dir / 'scoring_points.json', {'status': 'passed', 'items': scoring_points, 'generated_at': now_iso()})
    write_json(out_dir / 'dependency_graph.json', dependency_graph)
    write_json(out_dir / 'data_need_map.json', data_need_map)
    write_json(out_dir / 'output_need_map.json', output_need_map)
    (out_dir / 'trap_analysis.md').write_text('# Trap Analysis\n\n' + '\n'.join(f"- **{t['code']}**: {t['description']}" for t in traps) + '\n', encoding='utf-8')
    (out_dir / 'judge_expectation.md').write_text('# Judge Expectation\n\n' + '\n'.join(f'- {x}' for x in judge_expectation) + '\n', encoding='utf-8')
    report = {
        'status': 'failed' if failures else ('warning' if warnings else 'passed'),
        'gate': 'problem-intelligence',
        'target': target,
        'signals': signals,
        'artifacts': {k: True for k in artifacts},
        'failures': failures,
        'warnings': warnings,
        'generated_at': now_iso(),
    }
    write_json(case_dir / 'quality' / 'problem_intelligence_report.json', report)
    return report
