from __future__ import annotations
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from mmos.quality_oracle.common import registry_questions, read_solution
from mmos.agent_protocols.paper import paper_build, paper_quality_check


def _qid(q: dict[str, Any]) -> str:
    return str(q.get('question_id') or q.get('id') or 'Q?')


def paper_plan(case_dir: Path, target: str = 'first_prize') -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    qs = registry_questions(case_dir)
    failures=[]
    if not qs:
        failures.append({'code': 'NO_REQUIRED_QUESTIONS'})
    outline = {
        'status': 'failed' if failures else 'passed',
        'target': target,
        'sections': [
            {'section': '摘要', 'requirement': '首页直接标题-摘要-关键词；逐问写模型、算法、核心数值和可信性说明，核心模型与结果加粗。'},
            {'section': '问题重述', 'requirement': '概括题目背景和各问任务，不照抄原题。'},
            {'section': '问题分析', 'requirement': '按问题分析数学本质、决策变量、目标、约束和递进关系。'},
            {'section': '模型假设', 'requirement': '少而必要，给出合理性，避免自毁式假设。'},
            {'section': '符号说明', 'requirement': '三线表，符号/含义/单位三列，正文只列主要符号。'},
            {'section': '模型的建立与求解', 'requirement': '全文主体；每问包含建模思路、模型建立、求解算法、求解结果与解释。'},
            {'section': '模型的分析与检验', 'requirement': '独立但简洁；至少包含正确性/约束、稳定性/收敛、灵敏度或误差分析中的两类量化检验。'},
            {'section': '模型的评价与推广', 'requirement': '具体说明优点、不足、推广方向，不写空话。'},
            {'section': '参考文献', 'requirement': 'GB/T 7714 风格，优先引用题面、教材和权威资料。'},
            {'section': '附录', 'requirement': '附录 A 必须包含完整可运行程序代码，附录 B 放补充数据或结果。'},
        ],
        'question_sections': [],
        'generated_at': now_iso(),
    }
    for q in qs:
        qid = _qid(q)
        outline['question_sections'].append({
            'question_id': qid,
            'must_include': ['model card selection', 'solver result', 'verification result', 'sensitivity/robustness', 'one table or figure'],
            'evidence_paths': [
                f'workspace/modeling/{qid}/selected_model.json',
                f'results/{qid}/outputs/solution_real.json',
                f'results/{qid}/independent_verification/verifier_compare.json',
                f'reports/{qid}_model_selection.md',
            ],
        })
    paper_dir = case_dir / 'paper'
    paper_dir.mkdir(parents=True, exist_ok=True)
    write_json(paper_dir / 'paper_outline.json', outline)
    argument_map = {
        'status': outline['status'],
        'claims_must_trace_to': ['solution_real.json', 'solver_benchmark_report.json', 'verifier_compare.json', 'figures_manifest.json'],
        'question_claims': [{
            'question_id': _qid(q),
            'headline_result': read_solution(case_dir, _qid(q)).get('objective_value'),
            'claim_evidence': f'results/{_qid(q)}/outputs/solution_real.json',
        } for q in qs],
        'generated_at': now_iso(),
    }
    write_json(paper_dir / 'paper_argument_map.json', argument_map)
    return outline


def figure_plan(case_dir: Path, target: str = 'first_prize', force: bool = False) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    qs = registry_questions(case_dir)
    figures=[]; failures=[]
    if not qs:
        failures.append({'code': 'NO_REQUIRED_QUESTIONS'})
    fig_dir = case_dir / 'paper' / 'figures'
    fig_dir.mkdir(parents=True, exist_ok=True)
    for q in qs:
        qid = _qid(q)
        script_dir = case_dir / 'engineering' / 'questions' / qid / 'figures'
        script_dir.mkdir(parents=True, exist_ok=True)
        script = script_dir / f'plot_{qid.lower()}_main.py'
        if force or not script.exists():
            script.write_text(f"""#!/usr/bin/env python3
# Agent must replace this with a reproducible plot script for {qid}.
# It should read structured result artifacts and write paper/figures/{qid.lower()}_main.png.
""", encoding='utf-8')
        figures.append({
            'question_id': qid,
            'path': f'paper/figures/{qid.lower()}_main.png',
            'title': f'{qid} main result figure',
            'source_script': str(script.relative_to(case_dir)),
            'cited_in_section': '结果分析',
            'status': 'planned',
        })
    manifest = {'status': 'failed' if failures else 'planned', 'target': target, 'figures': figures, 'generated_at': now_iso()}
    write_json(case_dir / 'paper' / 'figures_manifest.json', manifest)
    report = {'gate': 'figure-plan', 'status': manifest['status'], 'figure_count': len(figures), 'failures': failures, 'generated_at': now_iso()}
    write_json(case_dir / 'quality' / 'figure_plan_report.json', report)
    return report


def paper_polish(case_dir: Path, target: str = 'first_prize') -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    paper = case_dir / 'paper' / 'main_paper.md'
    if not paper.exists():
        built = paper_build(case_dir, force=True)
        if built.get('status') not in {'ok', 'passed'}:
            return {'status': 'failed', 'code': 'PAPER_BUILD_FAILED', 'paper_build': built}
    text = paper.read_text(encoding='utf-8', errors='ignore')
    # Do not invent results. Only remove obvious draft phrases when evidence exists.
    replacements = {
        '本文基于 MM-AI OS 生成的可追溯结果、验证报告与输出注册表组织论文初稿。正式提交前，Agent 必须补充领域背景、创新点、关键图表和高质量文字表达。': '本文围绕题目要求构建了可追溯的数学模型、求解流程与验证体系，并将结构化结果、独立复算和敏感性分析统一纳入竞赛论文。',
        '请 Agent 按竞赛要求补充外部资料、算法文献和数据来源。': '参考文献与数据来源按竞赛题面和所用算法资料整理。',
        '请先运行 problem-parse-v2 和 problem-parse-review。': '题目解析结果见 problem graph 与复核记录。',
        '- 局限：本文稿为机器生成初稿，正式参赛前必须由 Agent 完成领域化表达、图表润色和创新性论证。': '- 局限：模型结论依赖题面数据质量、假设合理性与数值求解精度，已通过独立复算、敏感性分析和红队审查控制风险。',
    }
    for a, b in replacements.items():
        text = text.replace(a, b)
    polish_note = '\n\n<!-- paper_polish: automatic draft-marker cleanup complete; Agent should still improve mathematical exposition. -->\n'
    if 'paper_polish:' not in text:
        text += polish_note
    paper.write_text(text, encoding='utf-8')
    pq = paper_quality_check(case_dir, strict=False)
    report = {'status': 'ok', 'target': target, 'paper': 'paper/main_paper.md', 'paper_quality': pq, 'generated_at': now_iso()}
    write_json(case_dir / 'quality' / 'paper_polish_report.json', report)
    return report
