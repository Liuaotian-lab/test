from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mmos.contracts.manager import ensure_case_scaffold
from mmos.paper_latex.latex import compile_latex_pdf, paper_env_doctor


def main() -> None:
    case = ROOT / 'cases' / 'fixture_paper_env_doctor'
    if case.exists():
        shutil.rmtree(case)
    ensure_case_scaffold(case)

    doctor = paper_env_doctor(ROOT, case_dir=case)
    assert doctor['command'] == 'paper-env-doctor', doctor
    for key in ['xelatex', 'latexmk', 'pdftotext', 'tectonic']:
        assert key in doctor['checks'], doctor
        assert 'available' in doctor['checks'][key], doctor
    assert (case / 'quality' / 'paper_env_doctor.json').exists()

    tex_dir = case / 'paper_latex'
    tex_dir.mkdir(parents=True, exist_ok=True)
    (tex_dir / 'main_paper.tex').write_text(
        '\\documentclass{article}\\begin{document}paper env doctor fixture\\end{document}\n',
        encoding='utf-8',
    )

    old_path = os.environ.get('PATH', '')
    try:
        os.environ['PATH'] = ''
        compiled = compile_latex_pdf(case, engine='auto')
    finally:
        os.environ['PATH'] = old_path
    assert compiled['status'] == 'failed', compiled
    assert compiled['compile_instructions'] == 'paper_latex/compile_instructions.md', compiled
    assert (tex_dir / 'compile_instructions.md').exists()

    print('paper_env_doctor_checks passed', flush=True)


if __name__ == '__main__':
    main()
