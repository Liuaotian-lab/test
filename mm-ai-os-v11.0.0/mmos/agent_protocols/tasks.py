from __future__ import annotations
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso

PHASES = [
    'parse_review',
    'modeling',
    'solver_factory',
    'independent_verification',
    'paper_writing',
    'figure_design',
    'final_redteam',
]

PHASE_TITLES = {
    'parse_review': '题面解析复核协议',
    'modeling': '领域建模创新协议',
    'solver_factory': 'Solver 工厂协议',
    'independent_verification': '真正独立复算协议',
    'paper_writing': '完整竞赛论文写作协议',
    'figure_design': '图表设计与可复现绘图协议',
    'final_redteam': '最终红队审稿协议',
}

PHASE_OUTPUTS = {
    'parse_review': [
        'workspace/problem_graph.agent_review.json',
        'workspace/problem_graph.final.json',
    ],
    'modeling': [
        'workspace/modeling/{qid}_modeling_options.md',
        'contracts/questions/{qid}/model_candidates.json',
        'reports/{qid}_model_selection.md',
    ],
    'solver_factory': [
        'engineering/questions/{qid}/solve.py',
        'results/{qid}/outputs/solution_reduced.json',
        'results/{qid}/outputs/solution_real.json',
        'reports/{qid}_report.md',
    ],
    'independent_verification': [
        'engineering/questions/{qid}/verifiers/*.py',
        'results/{qid}/independent_verification/verifier_compare.json',
    ],
    'paper_writing': [
        'paper/main_paper.md',
        'quality/paper_quality_report.json',
    ],
    'figure_design': [
        'paper/figures_manifest.json',
        'paper/figures/*',
        'engineering/questions/{qid}/figures/*.py',
    ],
    'final_redteam': [
        'quality/red_team/final_human_style_review.md',
        'quality/agent_protocol_check.json',
    ],
}

PHASE_PROMPTS = {
    'parse_review': '''你现在是题面解析审稿人。不要默认接受 regex parser 的小问识别结果。逐项检查是否漏掉隐式小问、附件输出要求、依赖关系、单位、约束、数据字段。若需要修改，请写入 workspace/problem_graph.agent_review.json，并将 status 设为 passed。''',
    'modeling': '''你现在是数学建模竞赛建模负责人。每个小问至少提出 baseline、competition-strength、independent-verifier 三类候选模型。必须说明变量、目标、约束、数据输入、适用条件、失败点、复杂度、验证方法和 claim 级别。最后写入 model_candidates.json 与 model_selection.md。''',
    'solver_factory': '''你现在是工程化 solver 作者。必须把模型写成可运行代码，而不是只写思路。solution_real.json 必须包含 status、stage、quality_level、objective_value 或 metrics、diagnostics.constraints_checked、diagnostics.model_level、diagnostics.solver_variants、diagnostics.sensitivity_parameters 和 limitations。''',
    'independent_verification': '''你现在是独立复算审稿人。禁止调用主 solver 的函数；必须从原始数据或最终输出重新复算核心指标。使用另一套公式、采样或优化器输出 recomputed_value、solver_value、abs_error、rel_error、tolerance、pass/fail。''',
    'paper_writing': '''你现在是数学建模竞赛论文作者。必须生成完整论文：摘要、问题重述、假设、符号、模型建立、求解、结果分析、模型检验、灵敏度、优缺点、参考文献。所有关键数值必须可追溯到 result JSON/CSV/XLSX。''',
    'figure_design': '''你现在是竞赛论文图表设计师。每张图必须有数据来源、生成代码、标题、坐标轴/单位、正文引用位置。不得生成无法复现的装饰性图。''',
    'final_redteam': '''你现在是最终红队审稿人。查找过度最优性声明、缺失小问、未验证约束、论文-结果冲突、图表无来源、独立复算不足和上下文遗漏。P0/P1 必须阻断 final。''',
}


def _questions(case_dir: Path, question_id: str | None = None) -> list[dict[str, Any]]:
    reg = read_json(Path(case_dir) / 'registry' / 'questions_registry.json', {'questions': []}) or {'questions': []}
    qs = [q for q in reg.get('questions', []) if q.get('required', True) is not False]
    if question_id:
        qs = [q for q in qs if (q.get('question_id') or q.get('id')) == question_id]
    return qs


def _card_text(case_dir: Path, q: dict[str, Any], phase: str) -> str:
    qid = q.get('question_id') or q.get('id') or 'Q?'
    title = q.get('title') or qid
    qtype = q.get('type') or 'unknown'
    source = q.get('source_excerpt') or ''
    outputs = [x.format(qid=qid) for x in PHASE_OUTPUTS[phase]]
    lines = [
        f"# {qid} - {PHASE_TITLES[phase]}",
        '',
        f"- case_id: `{case_dir.name}`",
        f"- question_id: `{qid}`",
        f"- title: {title}",
        f"- routed_type: `{qtype}`",
        '',
        '## Agent role',
        '',
        PHASE_PROMPTS[phase],
        '',
        '## Required inputs',
        '',
        f"- `workspace/problem_graph.json` or `workspace/problem_graph.final.json`",
        f"- `contracts/questions/{qid}/`",
        f"- `data/raw/` and `data/manifest/data_manifest.json`",
        f"- `workspace/tool_recommendations/{qid}.tool_advice.json` if present",
        '',
        '## Required outputs',
        '',
    ]
    lines.extend([f"- `{o}`" for o in outputs])
    lines.extend([
        '',
        '## Non-negotiable rules',
        '',
        '- 不得只写文字说明而不落盘 artifact。',
        '- 不得用 placeholder、dummy、mock、toy solver 伪装完成。',
        '- 不得声称 global/certified optimal，除非有独立证明或穷举/严格界。',
        '- 所有关键数值必须可由结果文件或 verifier 复算。',
        '- 论文结论必须与 registered outputs 一致。',
        '',
        '## Gate commands to run after completion',
        '',
        '```bash',
        f'python scripts/mmtool.py contract-check {case_dir.name} --question {qid}',
        f'python scripts/mmtool.py solver-verify {case_dir.name} --result results/{qid}/outputs/solution_real.json --strict-schema',
        f'python scripts/mmtool.py verifier-compare {case_dir.name} --question {qid} --strict',
        f'python scripts/mmtool.py paper-quality-check {case_dir.name} --strict',
        '```',
        '',
    ])
    if source:
        lines.extend(['## Source excerpt', '', '```text', source[:2000], '```', ''])
    return '\n'.join(lines)


def generate_agent_tasks(case_dir: Path, question_id: str | None = None, phase: str = 'all', force: bool = False) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    phases = PHASES if phase in {'all', '*'} else [phase]
    invalid = [p for p in phases if p not in PHASES]
    if invalid:
        return {'status': 'failed', 'code': 'UNKNOWN_AGENT_PROTOCOL_PHASE', 'invalid': invalid, 'allowed': PHASES}
    qs = _questions(case_dir, question_id)
    if not qs:
        return {'status': 'failed', 'code': 'NO_REQUIRED_QUESTIONS', 'message': 'Run problem-parse-v2 and question-activate first.'}
    out_dir = case_dir / '.agent' / 'task_cards'
    out_dir.mkdir(parents=True, exist_ok=True)
    created=[]
    for q in qs:
        qid = q.get('question_id') or q.get('id')
        for ph in phases:
            dst = out_dir / f'{qid}_{ph}_protocol.md'
            if force or not dst.exists():
                dst.write_text(_card_text(case_dir, q, ph), encoding='utf-8')
            created.append(str(dst.relative_to(case_dir)))
        # Prepare artifact folders used by the protocols.
        (case_dir / 'workspace' / 'modeling').mkdir(parents=True, exist_ok=True)
        (case_dir / 'engineering' / 'questions' / qid / 'verifiers').mkdir(parents=True, exist_ok=True)
        (case_dir / 'engineering' / 'questions' / qid / 'figures').mkdir(parents=True, exist_ok=True)
        (case_dir / 'results' / qid / 'independent_verification' / 'plugins').mkdir(parents=True, exist_ok=True)
    status_path = case_dir / 'workspace' / 'agent_protocol_status.json'
    status = {
        'status': 'ok',
        'case_id': case_dir.name,
        'question_id': question_id,
        'phase': phase,
        'phases': phases,
        'cards': created,
        'generated_at': now_iso(),
    }
    write_json(status_path, status)
    return status


def agent_protocol_check(case_dir: Path, strict: bool = False, question_id: str | None = None) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    qs = _questions(case_dir, question_id)
    failures=[]; warnings=[]; evidence=[]
    if not qs:
        failures.append({'code': 'NO_REQUIRED_QUESTIONS'})
    for q in qs:
        qid = q.get('question_id') or q.get('id')
        for ph in PHASES:
            card = case_dir / '.agent' / 'task_cards' / f'{qid}_{ph}_protocol.md'
            item = {'question_id': qid, 'phase': ph, 'task_card': str(card.relative_to(case_dir)), 'task_card_exists': card.exists()}
            if not card.exists():
                warnings.append({'code': 'MISSING_AGENT_PROTOCOL_TASK_CARD', 'question_id': qid, 'phase': ph})
            evidence.append(item)
    global_contract = read_json(case_dir / 'contracts' / 'global' / 'agent_protocol_contract.json', {}) or {}
    required_flags = global_contract.get('required_for_final') or {}
    for flag, rel in {
        'parse_review': 'workspace/problem_graph.final.json',
        'paper_quality': 'quality/paper_quality_report.json',
    }.items():
        if required_flags.get(flag) and not (case_dir / rel).exists():
            failures.append({'code': f'MISSING_REQUIRED_{flag.upper()}', 'path': rel})
    status = 'failed' if failures or (strict and warnings) else ('warning' if warnings else 'passed')
    report = {'gate': 'agent-protocol-check', 'status': status, 'strict': strict, 'failures': failures, 'warnings': warnings, 'evidence': evidence, 'generated_at': now_iso()}
    write_json(case_dir / 'quality' / 'agent_protocol_check.json', report)
    return report
