from __future__ import annotations
from pathlib import Path
from typing import Any
import re
from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from mmos.quality_oracle.common import question_ids, read_solution

REQUIRED_SECTIONS = ['摘要','问题重述','模型假设','符号说明','模型建立','求解方法','结果分析','模型检验','灵敏度分析','模型优缺点','参考文献']


def _collect_question_reports(case_dir: Path, qid: str) -> str:
    chunks=[]
    for path in [case_dir / 'reports' / f'{qid}_report.md', case_dir / 'reports' / f'{qid}.md']:
        if path.exists():
            chunks.append(path.read_text(encoding='utf-8'))
    if not chunks:
        sol = read_solution(case_dir, qid)
        chunks.append(f"## {qid} 结果摘要\n\n- structured_status: `{sol.get('status')}`\n- objective_value: `{sol.get('objective_value')}`\n- metrics: `{sol.get('metrics')}`\n")
    return '\n\n'.join(chunks)


def paper_build(case_dir: Path, force: bool = False) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    paper_dir = case_dir / 'paper'
    paper_dir.mkdir(parents=True, exist_ok=True)
    out = paper_dir / 'main_paper.md'
    if out.exists() and not force:
        return {'status': 'ok', 'paper': str(out.relative_to(case_dir)), 'skipped_existing': True}
    graph = read_json(case_dir / 'workspace' / 'problem_graph.final.json', {}) or read_json(case_dir / 'workspace' / 'problem_graph.json', {}) or {}
    qs = question_ids(case_dir)
    lines = [
        '# 数学建模竞赛论文', '',
        '## 摘要', '',
        '本文基于 MM-AI OS 生成的可追溯结果、验证报告与输出注册表组织论文初稿。正式提交前，Agent 必须补充领域背景、创新点、关键图表和高质量文字表达。', '',
        '## 问题重述', '',
    ]
    if graph.get('questions'):
        for q in graph.get('questions', []):
            qid = q.get('question_id') or q.get('id')
            lines.append(f"- {qid}: {q.get('title') or q.get('source_excerpt','')[:120]}")
    else:
        lines.append('题面解析结果缺失；请先运行 problem-parse-v2 和 problem-parse-review。')
    lines.extend(['', '## 模型假设', '', '- 假设输入数据经过 data-audit 检查，缺失与异常处理在各小问模型中声明。', '- 假设所有强最优性声明均由独立验证或边界证明支持；否则仅声明为启发式/近似解。', '', '## 符号说明', '', '| 符号 | 含义 | 来源 |', '|---|---|---|', '| Q_i | 第 i 个小问 | problem_graph |', '| f | 目标函数或评价指标 | contract/objective_registry |', '', '## 模型建立', ''])
    for qid in qs:
        lines.extend([f'### {qid} 模型', '', _collect_question_reports(case_dir, qid), ''])
    lines.extend(['## 求解方法', '', '各小问的 solver 位于 `engineering/questions/<QID>/`，结构化结果位于 `results/<QID>/outputs/solution_real.json`。', '', '## 结果分析', ''])
    for qid in qs:
        sol = read_solution(case_dir, qid)
        lines.append(f"- {qid}: quality_level=`{sol.get('quality_level')}`, objective_value=`{sol.get('objective_value')}`, metrics=`{sol.get('metrics')}`")
    lines.extend(['', '## 模型检验', '', '独立复算结果应来自 `results/<QID>/independent_verification/verifier_compare.json`，并由 `verifier-compare --strict` 检查。', '', '## 灵敏度分析', '', '灵敏度分析结果应来自 `quality/sensitivity_report.json`，关键参数扰动必须覆盖模型核心假设。', '', '## 模型优缺点', '', '- 优点：流程可追溯、结果与输出注册表绑定、final gate 阻断假完成。', '- 局限：本文稿为机器生成初稿，正式参赛前必须由 Agent 完成领域化表达、图表润色和创新性论证。', '', '## 参考文献', '', '- 请 Agent 按竞赛要求补充外部资料、算法文献和数据来源。', ''])
    out.write_text('\n'.join(lines), encoding='utf-8')
    manifest = {'figures': [], 'generated_at': now_iso(), 'note': 'Populate with reproducible figure scripts and output paths.'}
    fig_manifest = paper_dir / 'figures_manifest.json'
    if not fig_manifest.exists():
        write_json(fig_manifest, manifest)
    return {'status': 'ok', 'paper': str(out.relative_to(case_dir)), 'question_count': len(qs), 'figures_manifest': str(fig_manifest.relative_to(case_dir))}


def _has_section(text: str, section: str) -> bool:
    return bool(re.search(rf'^#+\s*{re.escape(section)}\s*$', text, re.M))


def paper_quality_check(case_dir: Path, strict: bool = False) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    paper = case_dir / 'paper' / 'main_paper.md'
    failures=[]; warnings=[]
    if not paper.exists():
        failures.append({'code': 'MISSING_MAIN_PAPER', 'path': 'paper/main_paper.md'})
        text = ''
    else:
        text = paper.read_text(encoding='utf-8')
    for sec in REQUIRED_SECTIONS:
        if not _has_section(text, sec):
            failures.append({'code': 'MISSING_REQUIRED_PAPER_SECTION', 'section': sec})
    for qid in question_ids(case_dir):
        if qid not in text:
            failures.append({'code': 'QUESTION_NOT_REFERENCED_IN_PAPER', 'question_id': qid})
        sol = read_solution(case_dir, qid)
        val = sol.get('objective_value')
        if isinstance(val, (int, float)) and f'{val}' not in text and f'{float(val):.6g}' not in text:
            warnings.append({'code': 'OBJECTIVE_VALUE_NOT_EXPLICITLY_IN_PAPER', 'question_id': qid, 'objective_value': val})
    # Figure discipline: if figures are declared, each must have source_script and cited_in_section.
    fig_manifest = read_json(case_dir / 'paper' / 'figures_manifest.json', {}) or {}
    figures = fig_manifest.get('figures') or []
    if not figures:
        warnings.append({'code': 'NO_REPRODUCIBLE_FIGURES_DECLARED', 'path': 'paper/figures_manifest.json'})
    for fig in figures:
        if not fig.get('path') or not fig.get('source_script') or not fig.get('cited_in_section'):
            failures.append({'code': 'FIGURE_MANIFEST_ENTRY_INCOMPLETE', 'figure': fig})
        elif not (case_dir / fig['path']).exists():
            failures.append({'code': 'FIGURE_FILE_MISSING', 'path': fig['path']})
    # Generic-text warnings: useful for paper polish but not always blocking.
    generic_phrases = ['机器生成初稿', '请 Agent', '请先运行', '请补充']
    found_generic = [p for p in generic_phrases if p in text]
    if found_generic:
        (failures if strict else warnings).append({'code': 'PAPER_CONTAINS_DRAFT_OR_AGENT_PLACEHOLDER_TEXT', 'phrases': found_generic})
    status = 'failed' if failures else ('warning' if warnings else 'passed')
    report = {'gate': 'paper-quality-check', 'status': status, 'strict': strict, 'failures': failures, 'warnings': warnings, 'paper': 'paper/main_paper.md', 'generated_at': now_iso()}
    write_json(case_dir / 'quality' / 'paper_quality_report.json', report)
    return report
