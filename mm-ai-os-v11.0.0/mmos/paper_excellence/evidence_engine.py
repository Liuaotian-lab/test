from __future__ import annotations
from pathlib import Path
from typing import Any
import re, shutil

from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from mmos.kernel.hashing import sha256_file

CODE_EXTS = {'.py', '.m', '.r', '.R', '.jl', '.cpp', '.c', '.h', '.hpp', '.java', '.ipynb'}
QUESTION_RESULT_GLOBS = [
    'results/{qid}/outputs/solution_real.json',
    'results/{qid}/solution_real.json',
    'results/{qid}/outputs/*.json',
]


def _registry_questions(case_dir: Path) -> list[dict[str, Any]]:
    reg = read_json(case_dir / 'registry' / 'questions_registry.json', {}) or {}
    qs = reg.get('questions') if isinstance(reg, dict) else None
    if not qs:
        graph = read_json(case_dir / 'workspace' / 'problem_graph.json', {}) or {}
        qs = graph.get('questions') or []
    clean = []
    for i, q in enumerate(qs or [], 1):
        qid = q.get('question_id') or q.get('id') or f'Q{i}'
        if q.get('required', True) is not False:
            item = dict(q)
            item['question_id'] = qid
            clean.append(item)
    return clean


def _question_ids(case_dir: Path) -> list[str]:
    qs = _registry_questions(case_dir)
    return [q['question_id'] for q in qs] or ['Q1']


def _existing_result_files(case_dir: Path, qid: str) -> list[Path]:
    files: list[Path] = []
    for pat in QUESTION_RESULT_GLOBS:
        files.extend(case_dir.glob(pat.format(qid=qid)))
    return sorted({p.resolve() for p in files if p.is_file()})


def _status_of(path: Path) -> str | None:
    data = read_json(path, None)
    return data.get('status') if isinstance(data, dict) else None


def _has_pdf(case_dir: Path) -> bool:
    return any((case_dir / d).exists() and list((case_dir / d).glob('*.pdf')) for d in ['paper_latex', 'paper'])


def _semantic_ok(case_dir: Path) -> bool:
    p = case_dir / 'quality' / 'semantic_audit.json'
    status = _status_of(p)
    if status in {'passed', 'warning'}:
        return True
    # Also accept legacy workspace artifacts as evidence that audit ran.
    return (case_dir / 'workspace' / 'semantic_audit' / 'semantic_audit_report.md').exists()


def _claim_evidence_ok(case_dir: Path) -> bool:
    paths = [
        case_dir / 'quality' / 'claim_evidence_check.json',
        case_dir / 'workspace' / 'claim_evidence' / 'evidence_map.json',
        case_dir / 'paper' / 'evidence' / 'paper_evidence_graph.json',
    ]
    if any(p.exists() for p in paths):
        data = read_json(paths[0], {}) if paths[0].exists() else {}
        if isinstance(data, dict) and data.get('unsupported_claim_count', 0):
            return False
        return True
    return False


def paper_readiness_gate(case_dir: Path, target: str = 'national_first') -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    qids = _question_ids(case_dir)
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if not _semantic_ok(case_dir):
        blockers.append({'code': 'SEMANTIC_AUDIT_NOT_PASSED', 'message': 'Run semantic-audit before paper generation.'})

    missing_results = [qid for qid in qids if not _existing_result_files(case_dir, qid)]
    if missing_results:
        blockers.append({'code': 'MISSING_QUESTION_RESULTS', 'questions': missing_results})

    if not _claim_evidence_ok(case_dir):
        blockers.append({'code': 'CLAIM_EVIDENCE_NOT_READY', 'message': 'Build or check claim/paper evidence before writing final paper.'})

    fig_manifest = case_dir / 'paper' / 'figures_manifest.json'
    figs = (read_json(fig_manifest, {}) or {}).get('figures', []) if fig_manifest.exists() else []
    if not figs:
        warnings.append({'code': 'NO_FIGURE_ARGUMENT_MANIFEST', 'message': 'Core figures should be registered with source scripts and supported arguments.'})

    code_manifest = case_dir / 'paper' / 'appendix' / 'code_manifest.json'
    code_data = read_json(code_manifest, {}) or {}
    if not code_data.get('files'):
        blockers.append({'code': 'APPENDIX_FULL_CODE_NOT_BUILT', 'message': 'Run appendix-code-build and appendix-code-check before final paper build.'})

    award = read_json(case_dir / 'quality' / 'award_readiness_check.json', {}) or {}
    ceiling = award.get('current_award_ceiling') or 'unknown_before_review'
    if target == 'national_first' and ceiling not in {'national_first_candidate', 'national_first', 'A', 'S', 'unknown_before_review'}:
        warnings.append({'code': 'AWARD_CEILING_BELOW_TARGET', 'current_award_ceiling': ceiling})

    allowed = not blockers
    result = {
        'command': 'paper-readiness-gate',
        'status': 'passed' if allowed else 'failed',
        'paper_generation_allowed': allowed,
        'target': target,
        'current_award_ceiling': ceiling,
        'blocking_reasons': blockers,
        'warnings': warnings,
        'paper_section_policy': {
            'semantic_audit_as_section': False,
            'validation_as_large_section': True,
            'validation_should_be_concise': True,
            'appendix_full_code_required': True,
            'no_table_of_contents_page': True,
        },
        'generated_at': now_iso(),
    }
    write_json(case_dir / 'quality' / 'paper_readiness_gate.json', result)
    return result


def paper_evidence_graph(case_dir: Path, build: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    qids = _question_ids(case_dir)
    claims = []
    evidence_files = []
    for qid in qids:
        for p in _existing_result_files(case_dir, qid):
            evidence_files.append(p)
            data = read_json(p, {}) or {}
            metrics = data.get('metrics') or {}
            if metrics:
                for k, v in metrics.items():
                    if isinstance(v, (int, float, str)):
                        claims.append({
                            'claim_id': f'{qid}_{k}',
                            'question_id': qid,
                            'text': f'{qid} result metric {k} = {v}',
                            'claim_type': 'numeric_result',
                            'required_evidence': ['solver_result'],
                            'bound_evidence': [{'type': 'solver_result', 'path': str(p.relative_to(case_dir)), 'sha256': sha256_file(p)}],
                            'status': 'supported',
                        })
            else:
                claims.append({
                    'claim_id': f'{qid}_solution_result',
                    'question_id': qid,
                    'text': f'{qid} has solver-generated result artifact.',
                    'claim_type': 'solver_result',
                    'required_evidence': ['solver_result'],
                    'bound_evidence': [{'type': 'solver_result', 'path': str(p.relative_to(case_dir)), 'sha256': sha256_file(p)}],
                    'status': 'supported',
                })
    # Bind final outputs as evidence too.
    for p in sorted((case_dir / 'final_outputs').glob('**/*')) if (case_dir / 'final_outputs').exists() else []:
        if p.is_file():
            evidence_files.append(p)
    graph = {
        'command': 'paper-evidence-graph',
        'status': 'passed' if claims else 'warning',
        'claims': claims,
        'evidence_file_count': len({str(p) for p in evidence_files}),
        'missing_evidence': [] if claims else [{'code': 'NO_RESULT_CLAIMS_FOUND'}],
        'policy': 'Every key numeric claim in the front-stage paper should map to solver output, verifier output, final output, or figure source evidence.',
        'generated_at': now_iso(),
    }
    out = case_dir / 'paper' / 'evidence' / 'paper_evidence_graph.json'
    write_json(out, graph)
    md = ['# Paper Evidence Graph', '', f'Status: {graph["status"]}', '', '## Claims']
    for c in claims:
        ev = ', '.join(e['path'] for e in c.get('bound_evidence', []))
        md.append(f'- `{c["claim_id"]}`: {c["text"]} -> {ev}')
    (case_dir / 'paper' / 'evidence' / 'paper_evidence_report.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    write_json(case_dir / 'quality' / 'paper_evidence_graph.json', graph)
    return graph


def paper_argument_plan(case_dir: Path, target: str = 'national_first') -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    qids = _question_ids(case_dir)
    sections = [
        {'section': '摘要', 'intent': 'Condense model, algorithm, key results, and verification for all required questions.'},
        {'section': '一、问题重述', 'intent': 'Restate background, input, task, and required outputs without copying the original statement.'},
        {'section': '二、问题分析', 'intent': 'Explain the mathematical nature, dependencies among questions, and modeling route.'},
        {'section': '三、模型假设', 'intent': 'List necessary, defensible assumptions and their rationale.'},
        {'section': '四、符号说明', 'intent': 'Define core variables before formulas become dense.'},
        {'section': '五、模型的建立与求解', 'intent': 'For each question: preparation, model establishment, solution method, result analysis with concise embedded checks.'},
        {'section': '六、模型的分析与检验', 'intent': 'Present concise quantitative checks: correctness/feasibility, stability/convergence, sensitivity, error analysis or baseline comparison.'},
        {'section': '七、模型的评价与推广', 'intent': 'Summarize concrete strengths, limitations, and extension.'},
        {'section': '参考文献', 'intent': 'List cited mathematical, numerical, or domain references.'},
        {'section': '附录 A 完整程序代码', 'intent': 'Include complete executable code used to generate results.'},
    ]
    plan = {
        'command': 'paper-argument-plan',
        'status': 'passed',
        'target': target,
        'question_ids': qids,
        'front_stage_sections': sections,
        'forbidden_front_stage_sections': ['\\tableofcontents', '数据处理与语义审计', '语义审计', 'Award Readiness', 'Claim Evidence Gate'],
        'validation_policy': 'Model analysis/check must be an independent but concise sixth section; detailed correctness, feasibility, convergence and robustness evidence may be embedded in each question result analysis.',
        'generated_at': now_iso(),
    }
    out_dir = case_dir / 'paper' / 'planning'
    write_json(out_dir / 'paper_argument_map.json', plan)
    outline = ['# Paper Argument Plan', '', 'Final front-stage paper structure:']
    for sec in sections:
        outline.append(f'- {sec["section"]}: {sec["intent"]}')
    (out_dir / 'paper_outline.md').write_text('\n'.join(outline) + '\n', encoding='utf-8')
    write_json(case_dir / 'quality' / 'paper_argument_plan.json', plan)
    return plan


def figure_table_plan(case_dir: Path, target: str = 'national_first', force: bool = False) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    manifest_path = case_dir / 'paper' / 'figures_manifest.json'
    if manifest_path.exists() and not force:
        manifest = read_json(manifest_path, {}) or {}
    else:
        figures = []
        candidates = []
        for d in [case_dir / 'paper' / 'figures', case_dir / 'figures', case_dir / 'paper_latex' / 'figures']:
            if d.exists():
                candidates.extend(sorted(d.glob('*.png')) + sorted(d.glob('*.pdf')) + sorted(d.glob('*.jpg')))
        for p in candidates:
            rel = p.relative_to(case_dir)
            stem = p.stem
            # Try to infer source script.
            scripts = list(case_dir.glob(f'**/*{stem}*.py'))
            figures.append({
                'figure_id': stem,
                'path': str(rel),
                'title': stem.replace('_', ' '),
                'source_script': str(scripts[0].relative_to(case_dir)) if scripts else '',
                'paper_section': '五、模型的建立与求解',
                'argument_supported': 'Supports model result analysis; fill in a precise claim before final submission.',
                'required': True,
            })
        manifest = {'figures': figures, 'target': target, 'generated_at': now_iso()}
        write_json(manifest_path, manifest)
    tables = {'tables': [], 'target': target, 'generated_at': now_iso()}
    write_json(case_dir / 'paper' / 'tables_manifest.json', tables)
    result = {'command': 'figure-table-plan', 'status': 'passed' if manifest.get('figures') else 'warning', 'figure_count': len(manifest.get('figures', [])), 'table_count': 0, 'manifest_path': str(manifest_path.relative_to(case_dir))}
    write_json(case_dir / 'quality' / 'figure_table_plan.json', result)
    return result


def _safe_code_name(rel: Path) -> str:
    name = str(rel).replace('/', '__').replace('\\', '__')
    return re.sub(r'[^A-Za-z0-9_.-]', '_', name)


def appendix_code_build(case_dir: Path, question_id: str | None = None, all_questions: bool = False, force: bool = False) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    appendix = case_dir / 'paper' / 'appendix'
    code_out = appendix / 'code'
    if force and code_out.exists():
        shutil.rmtree(code_out)
    code_out.mkdir(parents=True, exist_ok=True)
    roots = [case_dir / 'engineering', case_dir / 'scripts']
    # Include case-level scripts such as build_v3.py when present.
    roots.extend([p for p in case_dir.glob('*.py') if p.is_file()])
    files: list[Path] = []
    for root in roots:
        if root.is_file() and root.suffix in CODE_EXTS:
            files.append(root)
        elif root.exists():
            files.extend([p for p in root.rglob('*') if p.is_file() and p.suffix in CODE_EXTS and '__pycache__' not in str(p)])
    if question_id:
        files = [p for p in files if f'/{question_id}/' in str(p).replace('\\','/') or p.name.lower().startswith(question_id.lower())]
    copied = []
    for p in sorted({x.resolve() for x in files}):
        try:
            rel = p.relative_to(case_dir)
        except ValueError:
            continue
        dst = code_out / _safe_code_name(rel)
        shutil.copy2(p, dst)
        copied.append({'source_path': str(rel), 'appendix_path': str(dst.relative_to(case_dir)), 'sha256': sha256_file(p), 'lines': sum(1 for _ in p.open('r', encoding='utf-8', errors='ignore')), 'included_in_appendix': True})
    tex_lines = [r'\clearpage', r'\appendixpage', r'\subsection*{附录 A\quad 完整程序代码}', r'\addcontentsline{toc}{section}{附录 A\quad 完整程序代码}']
    for i, item in enumerate(copied, 1):
        lang = 'Python' if item['source_path'].endswith('.py') else ''
        tex_lines.append(rf'\subsubsection*{{A.{i}\quad {item["source_path"]}}}')
        tex_lines.append(rf'\lstinputlisting[language={lang}]{{{item["appendix_path"]}}}')
    (appendix / 'appendix_code.tex').write_text('\n'.join(tex_lines) + '\n', encoding='utf-8')
    manifest = {'status': 'complete' if copied else 'missing', 'files': copied, 'file_count': len(copied), 'generated_at': now_iso(), 'full_executable_code_required': True}
    write_json(appendix / 'code_manifest.json', manifest)
    result = {'command': 'appendix-code-build', 'status': 'passed' if copied else 'failed', 'file_count': len(copied), 'manifest': str((appendix / 'code_manifest.json').relative_to(case_dir))}
    write_json(case_dir / 'quality' / 'appendix_code_build.json', result)
    return result


def appendix_code_check(case_dir: Path, strict: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    manifest = read_json(case_dir / 'paper' / 'appendix' / 'code_manifest.json', {}) or {}
    files = manifest.get('files') or []
    issues = []
    if not files:
        issues.append({'code': 'NO_APPENDIX_CODE_FILES'})
    # Require at least one file that looks like a solver or build script.
    names = ' '.join(f.get('source_path', '').lower() for f in files)
    if files and not any(tok in names for tok in ['solve', 'solver', 'optimize', 'run', 'build']):
        issues.append({'code': 'NO_CORE_SOLVER_OR_BUILD_CODE_DETECTED'})
    for f in files:
        p = case_dir / f.get('appendix_path', '')
        if not p.exists():
            issues.append({'code': 'APPENDIX_CODE_COPY_MISSING', 'path': f.get('appendix_path')})
        if f.get('lines', 0) < 5:
            issues.append({'code': 'APPENDIX_CODE_TOO_SHORT', 'path': f.get('source_path'), 'lines': f.get('lines')})
    status = 'failed' if strict and issues else ('warning' if issues else 'passed')
    result = {'command': 'appendix-code-check', 'status': status, 'file_count': len(files), 'issues': issues, 'requirement': 'Appendix must include complete executable code, not pseudocode fragments.'}
    write_json(case_dir / 'quality' / 'appendix_code_check.json', result)
    return result


def paper_redteam_review(case_dir: Path, target: str = 'national_first') -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    readiness = read_json(case_dir / 'quality' / 'paper_readiness_gate.json', {}) or {}
    arg = read_json(case_dir / 'quality' / 'paper_argument_check.json', {}) or {}
    evid = read_json(case_dir / 'quality' / 'paper_evidence_check.json', {}) or {}
    fig = read_json(case_dir / 'quality' / 'figure_argument_check.json', {}) or {}
    app = read_json(case_dir / 'quality' / 'appendix_code_check.json', {}) or {}
    major = []
    fatal = []
    for label, data in [('readiness', readiness), ('argument', arg), ('evidence', evid), ('figure', fig), ('appendix_code', app)]:
        if data.get('status') == 'failed':
            fatal.append({'module': label, 'issue': data.get('issues') or data.get('blocking_reasons') or data})
        elif data.get('status') == 'warning':
            major.append({'module': label, 'issue': data.get('issues') or data.get('warnings') or data})
    ceiling = 'national_first_candidate' if not fatal and not major else ('national_second' if not fatal else 'not_ready')
    result = {'command': 'paper-redteam-review', 'status': 'passed' if not fatal else 'failed', 'target': target, 'paper_award_ceiling': ceiling, 'fatal_flaws': fatal, 'major_deductions': major, 'minor_deductions': [], 'rewrite_required_sections': [], 'generated_at': now_iso()}
    write_json(case_dir / 'quality' / 'paper_redteam_review.json', result)
    return result


def paper_repair_dispatch(case_dir: Path) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    readiness = read_json(case_dir / 'quality' / 'paper_readiness_gate.json', {}) or {}
    red = read_json(case_dir / 'quality' / 'paper_redteam_review.json', {}) or {}
    tasks = []
    for b in readiness.get('blocking_reasons', []):
        code = b.get('code', 'PAPER_BLOCKER')
        tasks.append({'task_id': f'repair_{code.lower()}', 'severity': 'P0', 'source': 'paper-readiness-gate', 'issue': b, 'repair': _repair_for_code(code)})
    for f in red.get('fatal_flaws', []):
        tasks.append({'task_id': f'repair_redteam_{f.get("module","unknown")}', 'severity': 'P0', 'source': 'paper-redteam-review', 'issue': f, 'repair': 'Fix the underlying model/evidence/appendix issue and rerun paper checks.'})
    out_dir = case_dir / '.agent' / 'task_cards' / 'paper_driven_repairs'
    out_dir.mkdir(parents=True, exist_ok=True)
    for t in tasks:
        md = f"# {t['task_id']}\n\n- Severity: {t['severity']}\n- Source: {t['source']}\n- Issue: `{t['issue']}`\n- Required repair: {t['repair']}\n- Acceptance: rerun `paper-readiness-gate`, `appendix-code-check`, `paper-evidence-check`, and `paper-redteam-review`.\n"
        (out_dir / f"{t['task_id']}.md").write_text(md, encoding='utf-8')
    result = {'command': 'paper-repair-dispatch', 'status': 'passed', 'task_count': len(tasks), 'tasks': tasks, 'task_dir': str(out_dir.relative_to(case_dir))}
    write_json(case_dir / 'quality' / 'paper_repair_dispatch.json', result)
    return result


def _repair_for_code(code: str) -> str:
    return {
        'SEMANTIC_AUDIT_NOT_PASSED': 'Run semantic-audit and repair problem interpretation before writing.',
        'MISSING_QUESTION_RESULTS': 'Implement and run solvers for all required questions.',
        'CLAIM_EVIDENCE_NOT_READY': 'Build claim evidence map and bind each important result to solver/verifier artifacts.',
        'APPENDIX_FULL_CODE_NOT_BUILT': 'Run appendix-code-build and include complete executable code in the appendix.',
    }.get(code, 'Repair the underlying model, code, verification, or paper evidence before writing the final paper.')
