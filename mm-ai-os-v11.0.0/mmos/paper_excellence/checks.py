from __future__ import annotations
from pathlib import Path
import re, subprocess, shutil
from typing import Any
from mmos.kernel.jsonio import read_json, write_json

# Front-stage CUMCM structure. Internal OS sections such as semantic audit must not be required as paper chapters.
REQUIRED_SECTIONS = [
    '摘要', '问题重述', '问题分析', '模型假设', '符号说明',
    '模型的建立与求解', '模型的分析与检验', '模型的评价与推广', '参考文献', '附录'
]
FORBIDDEN_FRONT_STAGE_SECTIONS = ['\\tableofcontents', '数据处理与语义审计', '语义审计章节', 'Award Readiness', 'Claim Evidence Gate', 'Paper Evidence Graph']


def _paper_text(case_dir: Path) -> tuple[str, Path | None]:
    candidates = [
        case_dir / 'paper_latex' / 'main_paper.tex',
        case_dir / 'paper_latex' / 'main.tex',
        case_dir / 'paper' / 'main_paper.tex',
        case_dir / 'paper' / 'main_paper.md',
        case_dir / 'reports' / 'paper.md',
    ]
    for p in candidates:
        if p.exists():
            return p.read_text(encoding='utf-8', errors='ignore'), p
    return '', None


def pdf_text_check(case_dir: Path) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    pdfs = []
    for d in ['paper_latex', 'paper']:
        if (case_dir / d).exists():
            pdfs.extend(sorted((case_dir / d).glob('*.pdf')))
    if not pdfs:
        result = {'status': 'failed', 'reason': 'no_pdf_found'}
    else:
        pdf = pdfs[0]
        text = ''
        if shutil.which('pdftotext'):
            out = case_dir / 'paper_latex' / 'pdf_text_check.txt'
            out.parent.mkdir(parents=True, exist_ok=True)
            try:
                subprocess.run(['pdftotext', str(pdf), str(out)], check=False, timeout=20, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                text = out.read_text(encoding='utf-8', errors='ignore') if out.exists() else ''
            except Exception:
                text = ''
        result = {'status': 'passed' if len(text.strip()) >= 200 else 'failed', 'pdf': str(pdf), 'extracted_chars': len(text.strip()), 'requirement': 'PDF must contain searchable/checkable text, not full-page images.'}
    write_json(case_dir / 'quality' / 'pdf_text_check.json', result)
    return result


def paper_argument_check(case_dir: Path, strict: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    text, path = _paper_text(case_dir)
    def _has_section(sec: str) -> bool:
        if sec in text:
            return True
        aliases = {
            '摘要': ['摘\\quad 要', 'cumcmabstract'],
            '参考文献': ['referencespage', 'printbibliography'],
            '附录': ['appendixpage', 'appendix', '附录 A'],
            '模型的分析与检验': ['模型分析与检验', '模型的检验', '模型检验'],
            '模型的评价与推广': ['模型评价与推广', '模型的评价', '模型评价'],
        }
        return any(a in text for a in aliases.get(sec, []))
    missing = [sec for sec in REQUIRED_SECTIONS if not _has_section(sec)]
    forbidden = [sec for sec in FORBIDDEN_FRONT_STAGE_SECTIONS if sec in text]
    graph = read_json(case_dir / 'workspace' / 'problem_graph.json', {}) or read_json(case_dir / 'registry' / 'questions_registry.json', {}) or {'questions': []}
    qids = [q.get('question_id') or q.get('id') for q in graph.get('questions', []) if q.get('required', True) is not False]
    # Q1 may appear as 问题一, so accept either.
    cn = {'Q1': '问题一', 'Q2': '问题二', 'Q3': '问题三', 'Q4': '问题四', 'Q5': '问题五'}
    q_missing = [qid for qid in qids if qid and qid not in text and cn.get(qid, '') not in text]
    formula_count = len(re.findall(r'\\\(|\\\[|\$\$|\\begin\{equation\}|=', text))
    figure_refs = len(re.findall(r'图\s*\d+|figure|\\includegraphics', text, re.I))
    appendix_code_refs = len(re.findall(r'\\lstinputlisting|完整程序代码|附录 A', text))
    issues = []
    if missing:
        issues.append({'code': 'MISSING_CONTEST_PAPER_SECTIONS', 'missing': missing})
    if forbidden:
        issues.append({'code': 'INTERNAL_OS_SECTIONS_VISIBLE_IN_FINAL_PAPER', 'forbidden': forbidden})
    if q_missing:
        issues.append({'code': 'MISSING_QUESTION_COVERAGE', 'missing_questions': q_missing})
    if formula_count < 3:
        issues.append({'code': 'INSUFFICIENT_FORMULA_CHAIN', 'formula_like_count': formula_count})
    if figure_refs < 1:
        issues.append({'code': 'NO_ARGUMENT_FIGURES', 'figure_refs': figure_refs})
    if appendix_code_refs < 1:
        issues.append({'code': 'APPENDIX_FULL_CODE_NOT_REFERENCED'})
    status = 'failed' if strict and issues else ('warning' if issues else 'passed')
    result = {'status': status, 'paper_path': str(path) if path else None, 'missing_sections': missing, 'forbidden_sections': forbidden, 'missing_questions': q_missing, 'formula_like_count': formula_count, 'figure_refs': figure_refs, 'appendix_code_refs': appendix_code_refs, 'issues': issues, 'policy': 'Final CUMCM-style paper must have no directory, no explicit OS audit chapter, a concise independent 模型的分析与检验 chapter, a 模型的评价与推广 chapter, and complete executable code appendix.'}
    write_json(case_dir / 'quality' / 'paper_argument_check.json', result)
    return result


def paper_evidence_check(case_dir: Path, strict: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    text, path = _paper_text(case_dir)
    nums = re.findall(r'(?<![A-Za-z])\d+(?:\.\d+)?\s*(?:MPa|ms|s|rad/s|rad/ms|mm|cm|%|℃|°C|W|N|m)?', text)
    evidence_files = list((case_dir / 'results').glob('**/*.json')) if (case_dir / 'results').exists() else []
    evidence_files += list((case_dir / 'final_outputs').glob('**/*')) if (case_dir / 'final_outputs').exists() else []
    evidence_files += list((case_dir / 'paper' / 'evidence').glob('**/*.json')) if (case_dir / 'paper' / 'evidence').exists() else []
    evidence_files = [p for p in evidence_files if p.is_file()]
    issues = []
    if len(nums) >= 5 and len(evidence_files) < 3:
        issues.append({'code': 'NUMERIC_CLAIMS_WITH_WEAK_EVIDENCE_TRACE', 'numeric_claim_count': len(nums), 'evidence_file_count': len(evidence_files)})
    if not (case_dir / 'paper' / 'evidence' / 'paper_evidence_graph.json').exists() and not (case_dir / 'workspace' / 'claim_evidence' / 'evidence_map.json').exists():
        issues.append({'code': 'NO_PAPER_EVIDENCE_GRAPH'})
    status = 'failed' if strict and issues else ('warning' if issues else 'passed')
    result = {'status': status, 'numeric_claim_count': len(nums), 'evidence_file_count': len(evidence_files), 'issues': issues}
    write_json(case_dir / 'quality' / 'paper_evidence_check.json', result)
    return result


def figure_argument_check(case_dir: Path, strict: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    manifest_path = case_dir / 'paper' / 'figures_manifest.json'
    manifest = read_json(manifest_path, {}) or {}
    figs = manifest.get('figures') or manifest.get('items') or []
    issues = []
    for i, fig in enumerate(figs):
        missing = [k for k in ['path', 'argument_supported'] if not fig.get(k)]
        # source_script is strongly recommended but not always available for externally supplied figures; warn instead of hard fail.
        if missing:
            issues.append({'code': 'FIGURE_MISSING_ARGUMENT_TRACE', 'index': i, 'missing': missing})
        p = case_dir / str(fig.get('path', ''))
        if fig.get('path') and not p.exists():
            issues.append({'code': 'FIGURE_FILE_MISSING', 'path': fig.get('path')})
    if not figs:
        issues.append({'code': 'NO_FIGURE_MANIFEST', 'path': str(manifest_path.relative_to(case_dir))})
    status = 'failed' if strict and issues else ('warning' if issues else 'passed')
    result = {'status': status, 'figure_count': len(figs), 'issues': issues}
    write_json(case_dir / 'quality' / 'figure_argument_check.json', result)
    return result


# Clean CUMCM section policy used by the repaired v6.2 paper builder.
REQUIRED_SECTIONS = [
    '摘要', '问题重述', '问题分析', '模型假设', '符号说明',
    '模型的建立与求解', '模型的分析与检验', '模型的评价与推广', '参考文献', '附录'
]
FORBIDDEN_FRONT_STAGE_SECTIONS = ['\\tableofcontents', '数据处理与语义审计', '语义审计章节', 'Award Readiness', 'Claim Evidence Gate', 'Paper Evidence Graph']


def paper_argument_check(case_dir: Path, strict: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    text, path = _paper_text(case_dir)

    def _has_section(sec: str) -> bool:
        if sec in text:
            return True
        aliases = {
            '摘要': ['cumcmabstract'],
            '参考文献': ['referencespage', 'printbibliography'],
            '附录': ['appendixpage', 'appendix', '附录 A'],
            '模型的分析与检验': ['模型分析与检验', '模型的检验'],
            '模型的评价与推广': ['模型评价与推广', '模型的评价', '模型推广'],
        }
        return any(alias in text for alias in aliases.get(sec, []))

    missing = [sec for sec in REQUIRED_SECTIONS if not _has_section(sec)]
    forbidden = [sec for sec in FORBIDDEN_FRONT_STAGE_SECTIONS if sec in text]
    graph = read_json(case_dir / 'workspace' / 'problem_graph.json', {}) or read_json(case_dir / 'registry' / 'questions_registry.json', {}) or {'questions': []}
    qids = [q.get('question_id') or q.get('id') for q in graph.get('questions', []) if q.get('required', True) is not False]
    cn = {'Q1': '问题一', 'Q2': '问题二', 'Q3': '问题三', 'Q4': '问题四', 'Q5': '问题五'}
    q_missing = [qid for qid in qids if qid and qid not in text and cn.get(qid, '') not in text]
    formula_count = len(re.findall(r'\\\(|\\\[|\$\$|\\begin\{equation\}|=', text))
    figure_refs = len(re.findall(r'图\s*\d+|figure|\\includegraphics', text, re.I))
    appendix_code_refs = len(re.findall(r'\\lstinputlisting|完整程序代码|附录 A', text))
    issues = []
    if missing:
        issues.append({'code': 'MISSING_CONTEST_PAPER_SECTIONS', 'missing': missing})
    if forbidden:
        issues.append({'code': 'INTERNAL_OS_SECTIONS_VISIBLE_IN_FINAL_PAPER', 'forbidden': forbidden})
    if q_missing:
        issues.append({'code': 'MISSING_QUESTION_COVERAGE', 'missing_questions': q_missing})
    if formula_count < 3:
        issues.append({'code': 'INSUFFICIENT_FORMULA_CHAIN', 'formula_like_count': formula_count})
    if figure_refs < 1:
        issues.append({'code': 'NO_ARGUMENT_FIGURES', 'figure_refs': figure_refs})
    if appendix_code_refs < 1:
        issues.append({'code': 'APPENDIX_FULL_CODE_NOT_REFERENCED'})
    status = 'failed' if strict and issues else ('warning' if issues else 'passed')
    result = {
        'status': status,
        'paper_path': str(path) if path else None,
        'missing_sections': missing,
        'forbidden_sections': forbidden,
        'missing_questions': q_missing,
        'formula_like_count': formula_count,
        'figure_refs': figure_refs,
        'appendix_code_refs': appendix_code_refs,
        'issues': issues,
        'policy': 'Final CUMCM-style paper must have no directory, no explicit OS audit chapter, a concise independent model analysis/check chapter, an evaluation/extension chapter, and complete executable code appendix.',
    }
    write_json(case_dir / 'quality' / 'paper_argument_check.json', result)
    return result
