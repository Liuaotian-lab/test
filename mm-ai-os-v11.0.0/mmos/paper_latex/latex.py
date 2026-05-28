from __future__ import annotations
from pathlib import Path
import subprocess, shutil, re, json
from typing import Any
from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso


def _tool_version(name: str, args: list[str] | None = None) -> str | None:
    exe = shutil.which(name)
    if not exe:
        return None
    try:
        proc = subprocess.run(
            [exe, *(args or ['--version'])],
            text=True,
            encoding='utf-8',
            errors='replace',
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
        )
        return (proc.stdout or '').splitlines()[0][:240] if proc.stdout else 'available'
    except Exception:
        return 'available'


def paper_env_doctor(root: Path, case_dir: Path | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    case_dir = Path(case_dir).resolve() if case_dir else None
    tools = {
        'xelatex': {'required_for_pdf': True, 'version_args': ['--version']},
        'latexmk': {'required_for_pdf': False, 'version_args': ['--version']},
        'pdftotext': {'required_for_pdf_text_check': True, 'version_args': ['-v']},
        'tectonic': {'required_for_pdf': False, 'version_args': ['--version']},
    }
    checks: dict[str, Any] = {}
    for name, meta in tools.items():
        exe = shutil.which(name)
        checks[name] = {
            'available': bool(exe),
            'path': exe,
            'version': _tool_version(name, meta.get('version_args')) if exe else None,
            **{k: v for k, v in meta.items() if k != 'version_args'},
        }
    if checks['xelatex']['available']:
        compile_mode = 'latexmk_xelatex' if checks['latexmk']['available'] else 'direct_xelatex_twice'
    elif checks['tectonic']['available']:
        compile_mode = 'tectonic_experimental'
    else:
        compile_mode = 'source_only'
    blockers = []
    warnings = []
    if not checks['xelatex']['available'] and not checks['tectonic']['available']:
        blockers.append({'code': 'NO_LATEX_ENGINE', 'message': 'Install a Unicode-capable LaTeX engine such as XeLaTeX before contest PDF packaging.'})
    if not checks['pdftotext']['available']:
        blockers.append({'code': 'NO_PDF_TEXT_EXTRACTOR', 'message': 'pdftotext is required to verify the PDF is searchable/checkable text.'})
    if not checks['latexmk']['available'] and checks['xelatex']['available']:
        warnings.append({'code': 'LATEXMK_MISSING', 'fallback': 'direct_xelatex_twice'})
    status = 'ready' if not blockers else ('blocked' if not checks['xelatex']['available'] and not checks['tectonic']['available'] else 'degraded')
    result = {
        'command': 'paper-env-doctor',
        'status': status,
        'compile_mode': compile_mode,
        'checks': checks,
        'blockers': blockers,
        'warnings': warnings,
        'policy': 'Contest paper packaging requires a generated TeX source, successful PDF compile, and searchable text verification.',
        'generated_at': now_iso(),
    }
    if case_dir:
        write_json(case_dir / 'quality' / 'paper_env_doctor.json', result)
    else:
        write_json(root / 'docs' / 'PAPER_ENV_DOCTOR_LAST.json', result)
    return result


def _write_compile_instructions(case_dir: Path, report: dict[str, Any]) -> None:
    out = case_dir / 'paper_latex'
    out.mkdir(parents=True, exist_ok=True)
    lines = [
        '# LaTeX Compile Instructions',
        '',
        'The paper TeX source was generated, but the local PDF toolchain is not ready.',
        '',
        'Required for contest packaging:',
        '- XeLaTeX or another Unicode-capable LaTeX engine',
        '- pdftotext for searchable-text verification',
        '',
        'Recommended commands after installing TeX Live or MiKTeX:',
        '',
        '```bash',
        'python scripts/mmtool.py paper-env-doctor <case_id>',
        'python scripts/mmtool.py latex-paper-compile <case_id> --engine auto',
        'python scripts/mmtool.py pdf-text-check <case_id>',
        '```',
        '',
        'Current blockers:',
    ]
    for item in report.get('blockers', []):
        lines.append(f"- {item.get('code')}: {item.get('message')}")
    (out / 'compile_instructions.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def _escape(s: Any) -> str:
    s = str(s if s is not None else '')
    rep = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(rep.get(ch, ch) for ch in s)


def _questions(case_dir: Path) -> list[dict[str, Any]]:
    reg = read_json(case_dir / 'registry' / 'questions_registry.json', {}) or {}
    qs = reg.get('questions') if isinstance(reg, dict) else None
    if not qs:
        graph = read_json(case_dir / 'workspace' / 'problem_graph.json', {}) or {}
        qs = graph.get('questions') or []
    out = []
    for i, q in enumerate(qs or [], 1):
        if q.get('required', True) is False:
            continue
        item = dict(q)
        item['question_id'] = item.get('question_id') or item.get('id') or f'Q{i}'
        item['title'] = item.get('title') or item.get('task_summary') or item['question_id']
        out.append(item)
    return out or [{'question_id': 'Q1', 'title': '问题一'}]


def _title(case_dir: Path) -> str:
    corpus = case_dir / 'workspace' / 'problem_corpus.md'
    if corpus.exists():
        text = corpus.read_text(encoding='utf-8', errors='ignore')
        for line in text.splitlines():
            line = line.strip().strip('#').strip()
            if line and len(line) <= 60 and ('题' in line or '设计' in line or '模型' in line):
                return line
    return case_dir.name


def _solution(case_dir: Path, qid: str) -> dict[str, Any]:
    candidates = [case_dir / 'results' / qid / 'outputs' / 'solution_real.json', case_dir / 'results' / qid / 'solution_real.json']
    for p in candidates:
        data = read_json(p, None)
        if isinstance(data, dict):
            return data
    return {}


def _format_metric_table(metrics: dict[str, Any]) -> str:
    if not metrics:
        return '本问的核心数值结果见对应输出文件。'
    rows = []
    for k, v in list(metrics.items())[:12]:
        if isinstance(v, (list, dict)):
            continue
        rows.append((_escape(k), _escape(v)))
    if not rows:
        return '本问的核心数值结果见对应输出文件。'
    body = '\n'.join([f'{k} & {v} \\\\' for k, v in rows])
    return rf'''
\begin{{table}}[!htbp]
\centering
\caption{{{_escape('核心结果表')}}}
\begin{{tabularx}}{{0.92\textwidth}}{{lL}}
\toprule
指标 & 数值 \\
\midrule
{body}
\bottomrule
\end{{tabularx}}
\end{{table}}
'''


def _copy_template_assets(root: Path, out: Path) -> None:
    tpl = root / 'paper_templates' / 'cumcm_gold'
    if tpl.exists():
        for name in ['goldmodeling.sty', 'references.bib']:
            if (tpl / name).exists():
                shutil.copy2(tpl / name, out / name)
    if not (out / 'goldmodeling.sty').exists():
        (out / 'goldmodeling.sty').write_text(r'''
\NeedsTeXFormat{LaTeX2e}
\ProvidesPackage{goldmodeling}[fallback]
\RequirePackage[a4paper,left=2.5cm,right=2.5cm,top=2.5cm,bottom=2.5cm]{geometry}
\RequirePackage{setspace,indentfirst,fancyhdr,titlesec,caption,graphicx,subcaption,booktabs,longtable,tabularx,array,multirow,amsmath,amssymb,bm,mathtools,siunitx,algorithm,algpseudocode,enumitem,xcolor,listings,float,placeins,makecell,hyperref}
\linespread{1.25}\setlength{\parindent}{2em}\pagestyle{fancy}\fancyhf{}\fancyfoot[C]{\thepage}\renewcommand{\headrulewidth}{0pt}
\renewcommand{\thesection}{\chinese{section}}\titleformat{\section}{\centering\heiti\zihao{3}\bfseries}{\thesection、}{0pt}{}\titleformat{\subsection}{\heiti\zihao{4}\bfseries}{\thesubsection}{0.8em}{}
\newcommand{\papertitle}[1]{\begin{center}{\heiti\zihao{-2}\bfseries #1\par}\end{center}\vspace{0.8em}}
\newenvironment{cumcmabstract}{\begin{center}{\heiti\zihao{4}\bfseries 摘\quad 要}\end{center}\zihao{-4}\songti}{\par}
\newcommand{\keywords}[1]{\par\vspace{0.6em}\noindent{\heiti\bfseries 关键词：}#1\par}
\newcommand{\abstractemph}[1]{\textbf{#1}}\newcommand{\keyresult}[2]{\noindent\textbf{#1}\quad #2\par}
\newcommand{\referencespage}{\clearpage\section*{参考文献}}\newcommand{\appendixpage}{\clearpage\section*{附录}}
\newcolumntype{L}{>{\raggedright\arraybackslash}X}
\lstset{basicstyle=\ttfamily\scriptsize,numbers=left,breaklines=true,columns=fullflexible,frame=single,showstringspaces=false}
''', encoding='utf-8')


def _figures(case_dir: Path, out: Path) -> list[dict[str, Any]]:
    fig_out = out / 'figures'
    fig_out.mkdir(exist_ok=True)
    copied = []
    for d in [case_dir / 'paper' / 'figures', case_dir / 'figures', case_dir / 'paper_latex' / 'figures']:
        if d.exists():
            for p in sorted(list(d.glob('*.png')) + list(d.glob('*.pdf')) + list(d.glob('*.jpg'))):
                dst = fig_out / p.name
                if p.resolve() != dst.resolve():
                    shutil.copy2(p, dst)
                copied.append({'path': f'figures/{p.name}', 'title': p.stem.replace('_', ' ')})
    return copied


def _appendix_input(case_dir: Path, out: Path) -> str:
    app = case_dir / 'paper' / 'appendix' / 'appendix_code.tex'
    if app.exists():
        # Copy appendix code tree into paper_latex to keep relative paths valid.
        src_code = case_dir / 'paper' / 'appendix' / 'code'
        if src_code.exists():
            dst = out / 'paper' / 'appendix' / 'code'
            if dst.exists():
                shutil.rmtree(dst)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src_code, dst)
        dst_tex = out / 'appendix_code.tex'
        txt = app.read_text(encoding='utf-8')
        # Paths in app are relative to case dir; in paper_latex they need paper/appendix/code.
        txt = txt.replace('{paper/appendix/code/', '{paper/appendix/code/')
        dst_tex.write_text(txt, encoding='utf-8')
        return r'\input{appendix_code.tex}'
    return r'''\appendixpage
\subsection*{附录 A\quad 完整程序代码}
尚未生成完整程序代码附录。正式提交前必须运行 \texttt{appendix-code-build} 与 \texttt{appendix-code-check}。
'''


def _cn_question(qid: str, idx: int | None = None) -> str:
    m = {'Q1': '问题一', 'Q2': '问题二', 'Q3': '问题三', 'Q4': '问题四', 'Q5': '问题五', 'Q6': '问题六'}
    if qid in m:
        return m[qid]
    if idx is not None:
        nums = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
        if 0 < idx < len(nums):
            return f'问题{nums[idx]}'
    return qid


def build_latex_source(case_dir: Path, force: bool = False, template: str = 'cumcm_gold') -> dict[str, Any]:
    """Build a CUMCM-style LaTeX paper under v6.2 paper standard."""
    case_dir = Path(case_dir).resolve()
    root = Path(__file__).resolve().parents[2]
    out = case_dir / 'paper_latex'
    if force and out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    _copy_template_assets(root, out)
    figs = _figures(case_dir, out)
    title = _title(case_dir)
    qs = _questions(case_dir)
    evidence_graph = read_json(case_dir / 'paper' / 'evidence' / 'paper_evidence_graph.json', {}) or {}
    claim_count = len(evidence_graph.get('claims', []))

    abstract_parts = [f'本文针对{_escape(title)}，围绕题目给出的多个子问题，建立从题意分析、模型构建、数值求解到结果检验的统一数学建模框架。首页直接给出摘要和关键词；关键模型、算法和核心结果在摘要中加粗，以便评委快速定位答案。']
    for idx, q in enumerate(qs, 1):
        qid = q['question_id']
        qname = _cn_question(qid, idx)
        sol = _solution(case_dir, qid)
        metrics = sol.get('metrics') or {}
        metric_bits = []
        for k, v in list(metrics.items())[:2]:
            if not isinstance(v, (list, dict)):
                metric_bits.append(f'\\abstractemph{{{_escape(k)}={_escape(v)}}}')
        metric_text = '，得到' + '、'.join(metric_bits) if metric_bits else '，并得到题目要求的输出文件和核心数值结果'
        abstract_parts.append(f'针对{qname}，根据该问的决策变量、目标函数和约束条件建立相应的\\abstractemph{{数学模型}}，采用\\abstractemph{{数值求解与结果校核}}方法{metric_text}。')
    abstract_parts.append(f'最后，本文在模型的分析与检验中给出约束可行性、稳定性、灵敏度或误差来源说明；关键结论由求解文件、图表和证据图谱支撑，共登记 {claim_count} 条证据声明，完整程序代码列入附录。')
    abstract = '\n\n'.join(abstract_parts)

    q_sections = []
    for idx, q in enumerate(qs, 1):
        qid = q['question_id']
        qname = _cn_question(qid, idx)
        sol = _solution(case_dir, qid)
        metrics = sol.get('metrics') or {}
        q_sections.append(rf'''
\subsection{{{qname}模型的建立与求解}}
\subsubsection{{建模思路}}
本问首先根据题意明确状态变量、决策变量、目标函数和约束条件，再将附件数据或题面参数转化为模型参数。模型建立时避免直接套用历史题答案，而是从该问的数学本质出发构造可计算表达式。

\subsubsection{{模型建立}}
设状态向量为 $x(t)$，决策变量为 $u$，目标函数为 $J(u)$，可行域为 $\Omega$。本问的基本优化或求解框架写为
\begin{{equation}}
  \max_{{u\in\Omega}} J(u),\qquad \text{{s.t.}}\quad F(x,\dot x,u,t)=0,
\end{{equation}}
其中 $F$ 表示由题意、约束和数据共同确定的模型方程。具体方程、参数和求解流程由本问可运行程序实现。

\subsubsection{{求解算法}}
采用数值积分、参数搜索、优化算法或统计计算对模型进行求解。求解过程中保存中间结果、核心指标和最终输出文件，关键程序见附录 A。

\subsubsection{{求解结果与解释}}
{_format_metric_table(metrics)}
上述结果应结合题意进行解释，并检查是否满足题设区间、单位、输出格式和主要物理、统计或优化约束。
''')
    fig_tex = ''
    for i, fig in enumerate(figs[:8], 1):
        fig_tex += rf'''
\begin{{figure}}[!htbp]
\centering
\includegraphics[width=0.78\textwidth]{{{fig['path']}}}
\caption{{{_escape(fig['title'])}}}
\label{{fig:auto_{i}}}
\end{{figure}}
'''
    appendix = _appendix_input(case_dir, out)
    tex = rf'''
\documentclass[UTF8,a4paper,12pt]{{ctexart}}
\usepackage{{goldmodeling}}
\begin{{document}}
\papertitle{{{_escape(title)}}}
\begin{{cumcmabstract}}
{abstract}
\keywords{{数学建模；模型检验；数值优化；三线表；完整代码附录}}
\end{{cumcmabstract}}

\section{{问题重述}}
本文研究对象由题面给出，并包含若干相互关联的子问题。各子问题分别要求建立模型、求解参数、输出文件或给出优化方案。本文将原始任务重述为：在题目数据与约束条件下，构建能够解释系统规律并生成可复现数值结果的数学模型。

\section{{问题分析}}
本题的关键是把自然语言任务转化为数学对象：明确每问的决策变量、目标函数、约束条件和输出形式。前面问题通常提供基础模型或参数识别，后续问题在此基础上加入优化、预测、控制、评价或鲁棒性要求。因此，本文按问题逐一建立模型，并在最后通过模型检验和评价统一说明结果可信性。

\section{{模型假设}}
\begin{{enumerate}}
  \item 题目所给数据、图示和附件能够代表研究对象的主要规律；
  \item 未明确给出的高阶效应在模型评价中作为局限说明，不强行作为硬约束；
  \item 所有单位、时间、角度、频率、区间和输出格式均按题面语义解释；
  \item 数值求解、图表生成和结果输出均由附录完整程序复现。
\end{{enumerate}}

\section{{符号说明}}
\begin{{table}}[!htbp]
\centering
\caption{{主要符号说明}}
\begin{{tabularx}}{{0.92\textwidth}}{{cLcc}}
\toprule
符号 & 含义 & 单位 & 备注 \\
\midrule
$x(t)$ & 状态变量向量 & - & 由各小问模型确定 \\
$u$ & 决策变量或控制参数 & - & 由目标函数优化确定 \\
$J(u)$ & 目标函数或评价指标 & - & 可为最大化或最小化 \\
$\Omega$ & 可行域 & - & 由题设约束和模型约束共同确定 \\
\bottomrule
\end{{tabularx}}
\end{{table}}

\section{{模型的建立与求解}}
{''.join(q_sections)}
{fig_tex}

\section{{模型的分析与检验}}
\subsection{{正确性与约束可行性检验}}
对各问求解结果，首先检查其是否满足题目给定的变量范围、输出文件格式和主要硬约束。若存在目标函数、区间约束或物理、统计边界，则在结果表或文字说明中逐项核对。

\subsection{{稳定性与收敛性说明}}
对需要数值积分、搜索或优化的模型，应比较不同步长、不同网格或不同初值下关键结果的变化。若关键指标变化较小，则说明计算结果具有较好的数值稳定性；若变化较大，应回到模型或算法部分重新改进。

\subsection{{灵敏度与误差分析}}
选取对结果影响较大的参数进行扰动，观察目标函数和核心结果变化。误差主要来自数据精度、离散步长、模型假设和未建模高阶效应。必要时可用图表展示扰动结果。

\section{{模型的评价与推广}}
\subsection{{模型优点}}
本文模型结构清晰，能够从题意出发形成变量、目标、约束、求解和检验闭环；核心结果由程序输出、图表和证据文件支撑，便于复核。
\subsection{{模型不足}}
模型结论仍依赖题面数据质量、假设合理性和数值求解精度。对于题面未给出的高阶机制或边界条件，本文只能进行风险说明，不能作无依据强结论。
\subsection{{模型推广}}
该建模框架可推广到多小问、多附件、多目标优化或复杂系统仿真类问题。若有更充分数据，可进一步加入鲁棒优化、随机扰动检验和更高保真模型。

\referencespage
\begin{{enumerate}}[label={{[\arabic*]}}]
\item 全国大学生数学建模竞赛论文格式规范。
\item 题目附件与原始数据。
\item 数值分析、优化理论及相关领域建模参考资料。
\end{{enumerate}}

{appendix}
\end{{document}}
'''
    tex_path = out / 'main_paper.tex'
    tex_path.write_text(tex, encoding='utf-8')
    report = {'command': 'latex-paper-build', 'status': 'passed', 'template': template, 'tex_path': str(tex_path.relative_to(case_dir)), 'front_stage_policy': 'No TOC; CUMCM title-abstract-keywords first page; Chinese major sections; concise model analysis/check chapter; model evaluation/promotion chapter; appendix full executable code required.', 'generated_at': now_iso()}
    write_json(case_dir / 'quality' / 'latex_paper_build.json', report)
    return report


def compile_latex_pdf(case_dir: Path, force: bool = False, engine: str = 'auto') -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    src = case_dir / 'paper_latex' / 'main_paper.tex'
    if force or not src.exists():
        build_latex_source(case_dir, force=force)
    env = paper_env_doctor(Path(__file__).resolve().parents[2], case_dir=case_dir)
    cmd = None
    if engine not in {'auto', 'xelatex', 'latexmk', 'tectonic'}:
        report = {'command': 'latex-paper-compile', 'status': 'failed', 'error': f'unsupported engine: {engine}', 'environment': env}
        write_json(case_dir / 'quality' / 'latex_paper_compile.json', report)
        return report
    if engine in {'auto', 'latexmk'} and shutil.which('latexmk'):
        cmd = ['latexmk', '-xelatex', '-interaction=nonstopmode', '-halt-on-error', 'main_paper.tex']
    elif engine in {'auto', 'xelatex'} and shutil.which('xelatex'):
        cmd = ['xelatex', '-interaction=nonstopmode', '-halt-on-error', 'main_paper.tex']
    elif engine in {'auto', 'tectonic'} and shutil.which('tectonic'):
        cmd = ['tectonic', 'main_paper.tex']
    else:
        report = {
            'command': 'latex-paper-compile',
            'status': 'failed',
            'error': 'No supported LaTeX engine found for this request.',
            'engine': engine,
            'environment': env,
            'blockers': env.get('blockers', []),
            'tex_path': str(src.relative_to(case_dir)) if src.exists() else None,
            'compile_instructions': 'paper_latex/compile_instructions.md',
            'generated_at': now_iso(),
        }
        _write_compile_instructions(case_dir, report)
        write_json(case_dir / 'quality' / 'latex_paper_compile.json', report)
        return report
    # Run twice for references when using xelatex directly.
    proc = subprocess.run(cmd, cwd=str(src.parent), text=True, encoding='utf-8', errors='replace', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=240)
    if cmd[0] == 'xelatex' and proc.returncode == 0:
        proc2 = subprocess.run(cmd, cwd=str(src.parent), text=True, encoding='utf-8', errors='replace', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=240)
        proc.stdout = (proc.stdout or '') + (proc2.stdout or '')
        proc.returncode = proc2.returncode
    pdf = src.parent / 'main_paper.pdf'
    text = ''
    if pdf.exists() and shutil.which('pdftotext'):
        try:
            text = subprocess.run(['pdftotext', str(pdf), '-'], text=True, encoding='utf-8', errors='replace', stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30).stdout
        except Exception:
            text = ''
    text_searchable = len(text.strip()) > 100
    status = 'passed' if proc.returncode == 0 and pdf.exists() and text_searchable else 'failed'
    failures = []
    if proc.returncode != 0:
        failures.append({'code': 'LATEX_COMPILE_FAILED', 'return_code': proc.returncode})
    if not pdf.exists():
        failures.append({'code': 'PDF_NOT_CREATED'})
    if pdf.exists() and not shutil.which('pdftotext'):
        failures.append({'code': 'PDF_TEXT_CHECK_UNAVAILABLE'})
    elif pdf.exists() and not text_searchable:
        failures.append({'code': 'PDF_NOT_SEARCHABLE_OR_TOO_SHORT', 'extracted_chars': len(text.strip())})
    report = {
        'command': 'latex-paper-compile',
        'status': status,
        'engine': cmd[0],
        'pdf_path': str(pdf.relative_to(case_dir)) if pdf.exists() else None,
        'text_searchable': text_searchable,
        'extracted_chars': len(text.strip()),
        'failures': failures,
        'environment': env,
        'log_tail': (proc.stdout or '')[-4000:],
        'generated_at': now_iso(),
    }
    write_json(case_dir / 'quality' / 'latex_paper_compile.json', report)
    return report


def _clean_title(case_dir: Path) -> str:
    corpus = case_dir / 'workspace' / 'problem_corpus.md'
    if corpus.exists():
        text = corpus.read_text(encoding='utf-8', errors='ignore')
        for line in text.splitlines():
            line = line.strip().strip('#').strip()
            if 6 <= len(line) <= 80 and any(token in line for token in ['题', '模型', '设计', '高压油管']):
                return line
    return case_dir.name


def _clean_cn_question(qid: str, idx: int) -> str:
    names = ['零', '一', '二', '三', '四', '五', '六']
    return f'问题{names[idx]}' if 0 < idx < len(names) else qid


def _clean_metric_table(metrics: dict[str, Any]) -> str:
    rows = []
    for key, value in list((metrics or {}).items())[:12]:
        if isinstance(value, (list, dict)):
            continue
        rows.append(f'{_escape(key)} & {_escape(value)} \\\\')
    if not rows:
        rows.append('待生成核心指标 & 需由 solver 输出绑定 \\\\')
    body = '\n'.join(rows)
    return rf'''
\begin{{table}}[!htbp]
\centering
\caption{{核心结果表}}
\begin{{tabularx}}{{0.92\textwidth}}{{lL}}
\toprule
指标 & 数值 \\
\midrule
{body}
\bottomrule
\end{{tabularx}}
\end{{table}}
'''


def _clean_appendix(case_dir: Path, out: Path) -> str:
    manifest = read_json(case_dir / 'paper' / 'appendix' / 'code_manifest.json', {}) or {}
    files = manifest.get('files') or []
    if files:
        lines = [r'\appendixpage', r'\subsection*{附录 A\quad 完整程序代码}']
        for i, item in enumerate(files, 1):
            appendix_path = item.get('appendix_path', '')
            src = item.get('source_path', appendix_path)
            src_file = case_dir / appendix_path
            if src_file.exists():
                dst = out / appendix_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src_file.resolve() != dst.resolve():
                    shutil.copy2(src_file, dst)
                lang = 'Python' if str(src).endswith('.py') else ''
                lines.append(rf'\subsubsection*{{A.{i}\quad {_escape(src)}}}')
                lines.append(rf'\lstinputlisting[language={lang}]{{{appendix_path}}}')
        return '\n'.join(lines)
    return r'''\appendixpage
\subsection*{附录 A\quad 完整程序代码}
尚未生成完整程序代码附录。正式提交前必须运行 \texttt{appendix-code-build} 和 \texttt{appendix-code-check}。'''


def build_latex_source(case_dir: Path, force: bool = False, template: str = 'cumcm_gold') -> dict[str, Any]:
    """Build a readable CUMCM-style LaTeX source with clean Chinese text."""
    case_dir = Path(case_dir).resolve()
    root = Path(__file__).resolve().parents[2]
    out = case_dir / 'paper_latex'
    if force and out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    _copy_template_assets(root, out)
    figs = _figures(case_dir, out)
    title = _clean_title(case_dir)
    qs = _questions(case_dir)
    evidence_graph = read_json(case_dir / 'paper' / 'evidence' / 'paper_evidence_graph.json', {}) or {}
    claim_count = len(evidence_graph.get('claims', []))

    abstract_parts = [
        f'本文针对{_escape(title)}，围绕题目给出的多个子问题，建立从题意分析、模型构建、数值求解到结果检验的统一数学建模流程。论文首页直接给出摘要和关键词，不设置目录页；核心模型、算法和关键结果应在摘要中明确呈现，便于评委快速定位答案。'
    ]
    for idx, q in enumerate(qs, 1):
        qid = q['question_id']
        sol = _solution(case_dir, qid)
        metrics = sol.get('metrics') or {}
        metric_bits = []
        for key, value in list(metrics.items())[:2]:
            if not isinstance(value, (list, dict)):
                metric_bits.append(rf'\abstractemph{{{_escape(key)}={_escape(value)}}}')
        metric_text = '，得到' + '、'.join(metric_bits) if metric_bits else '，并输出待证据绑定的核心数值结果'
        abstract_parts.append(f'针对{_clean_cn_question(qid, idx)}，根据该问的决策变量、目标函数和约束条件建立相应的\\abstractemph{{数学模型}}，采用\\abstractemph{{数值求解与结果校核}}方法{metric_text}。')
    abstract_parts.append(f'最后，本文在模型的分析与检验中给出约束可行性、稳定性、灵敏度或误差来源说明；关键结论由求解文件、图表和证据图支撑，共登记 {claim_count} 条证据声明，完整程序代码列入附录。')
    abstract = '\n\n'.join(abstract_parts)

    q_sections = []
    for idx, q in enumerate(qs, 1):
        qid = q['question_id']
        q_sections.append(rf'''
\subsection{{{_clean_cn_question(qid, idx)}模型的建立与求解}}
\subsubsection{{建模思路}}
本问首先根据题意明确状态变量、决策变量、目标函数和约束条件，再将附件数据或题面参数转化为模型参数。模型建立时避免直接套用模板，而是从该问的物理机制、统计规律或优化目标出发构造可计算表达式。

\subsubsection{{模型建立}}
设状态向量为 $x(t)$，决策变量为 $u$，目标函数为 $J(u)$，可行域为 $\Omega$。本问的基本优化或求解框架写为
\begin{{equation}}
  \max_{{u\in\Omega}} J(u),\qquad \mathrm{{s.t.}}\quad F(x,\dot x,u,t)=0,
\end{{equation}}
其中 $F$ 表示由题意、约束和数据共同确定的模型方程。具体方程、参数和求解流程由本问可运行程序实现。

\subsubsection{{求解算法}}
采用数值积分、参数搜索、优化算法或统计计算对模型进行求解。求解过程中保存中间结果、核心指标和最终输出文件，关键程序见附录 A。

\subsubsection{{求解结果与解释}}
{_clean_metric_table(_solution(case_dir, qid).get('metrics') or {{}})}
上述结果应结合题意进行解释，并检查是否满足题设区间、单位、输出格式和主要物理、统计或优化约束。
''')
    fig_tex = ''
    for i, fig in enumerate(figs[:8], 1):
        fig_tex += rf'''
\begin{{figure}}[!htbp]
\centering
\includegraphics[width=0.78\textwidth]{{{fig['path']}}}
\caption{{{_escape(fig['title'])}}}
\label{{fig:auto_{i}}}
\end{{figure}}
'''

    tex = rf'''
\documentclass[UTF8,a4paper,12pt]{{ctexart}}
\usepackage{{goldmodeling}}
\begin{{document}}
\papertitle{{{_escape(title)}}}
\begin{{cumcmabstract}}
{abstract}
\keywords{{数学建模；模型检验；数值优化；三线表；完整代码附录}}
\end{{cumcmabstract}}

\section{{问题重述}}
本文研究对象由题面给出，并包含若干相互关联的子问题。各子问题分别要求建立模型、求解参数、输出文件或给出优化方案。本文将原始任务重述为：在题目数据与约束条件下，构建能够解释系统规律并生成可复现数值结果的数学模型。

\section{{问题分析}}
本题的关键是把自然语言任务转化为数学对象：明确每问的决策变量、目标函数、约束条件和输出形式。前面问题通常提供基础模型或参数识别，后续问题在此基础上加入优化、预测、控制、评价或鲁棒性要求。因此，本文按问题逐一建立模型，并在最后通过模型检验和评价统一说明结果可信性。

\section{{模型假设}}
\begin{{enumerate}}
  \item 题目所给数据、图示和附件能够代表研究对象的主要规律；
  \item 未明确给出的高阶效应在模型评价中作为局限说明，不强行作为硬约束；
  \item 所有单位、时间、角度、频率、区间和输出格式均按题面语义解释；
  \item 数值求解、图表生成和结果输出均由附录完整程序复现。
\end{{enumerate}}

\section{{符号说明}}
\begin{{table}}[!htbp]
\centering
\caption{{主要符号说明}}
\begin{{tabularx}}{{0.92\textwidth}}{{cLcc}}
\toprule
符号 & 含义 & 单位 & 备注 \\
\midrule
$x(t)$ & 状态变量向量 & -- & 由各小问模型确定 \\
$u$ & 决策变量或控制参数 & -- & 由目标函数优化确定 \\
$J(u)$ & 目标函数或评价指标 & -- & 可为最大化或最小化 \\
$\Omega$ & 可行域 & -- & 由题设约束和模型约束共同确定 \\
\bottomrule
\end{{tabularx}}
\end{{table}}

\section{{模型的建立与求解}}
{''.join(q_sections)}
{fig_tex}

\section{{模型的分析与检验}}
\subsection{{正确性与约束可行性检验}}
对各问求解结果，首先检查其是否满足题目给定的变量范围、输出文件格式和主要硬约束。若存在目标函数、区间约束或物理、统计边界，则在结果表或文字说明中逐项核对。

\subsection{{稳定性与收敛性说明}}
对需要数值积分、搜索或优化的模型，应比较不同步长、不同网格或不同初值下关键结果的变化。若关键指标变化较小，则说明计算结果具有较好的数值稳定性；若变化较大，应回到模型或算法部分重新改进。

\subsection{{灵敏度与误差分析}}
选取对结果影响较大的参数进行扰动，观察目标函数和核心结果变化。误差主要来自数据精度、离散步长、模型假设和未建模高阶效应。

\section{{模型的评价与推广}}
\subsection{{模型优点}}
本文模型结构清晰，能够从题意出发形成变量、目标、约束、求解和检验闭环；核心结果由程序输出、图表和证据文件支撑，便于复核。
\subsection{{模型不足}}
模型结论仍依赖题面数据质量、假设合理性和数值求解精度。对题面未给出的高阶机制或边界条件，本文只能进行风险说明，不能作无依据强结论。
\subsection{{模型推广}}
该建模框架可推广到多小问、多附件、多目标优化或复杂系统仿真类问题。若有更充分数据，可进一步加入鲁棒优化、随机扰动检验和更高保真模型。

\referencespage
\begin{{enumerate}}[label={{[\arabic*]}}]
\item 全国大学生数学建模竞赛论文格式规范。
\item 题目附件与原始数据。
\item 数值分析、优化理论及相关领域建模参考资料。
\end{{enumerate}}

{_clean_appendix(case_dir, out)}
\end{{document}}
'''
    tex_path = out / 'main_paper.tex'
    tex_path.write_text(tex, encoding='utf-8')
    report = {
        'command': 'latex-paper-build',
        'status': 'passed',
        'template': template,
        'tex_path': str(tex_path.relative_to(case_dir)),
        'front_stage_policy': 'No TOC; CUMCM title-abstract-keywords first page; Chinese major sections; concise model analysis/check chapter; model evaluation/promotion chapter; appendix full executable code required.',
        'generated_at': now_iso(),
    }
    write_json(case_dir / 'quality' / 'latex_paper_build.json', report)
    return report
