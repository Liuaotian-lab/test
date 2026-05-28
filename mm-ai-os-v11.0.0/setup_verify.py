#!/usr/bin/env python3
"""
MM-AI OS 7.4.0-candidate-official-split — Environment Verification Script

Run this from the project root directory:
    python setup_verify.py

This script verifies:
1.  Python version and mmos package integrity
2.  LaTeX toolchain availability (xelatex, latexmk, pdftotext)
3.  Python scientific computing stack (numpy, scipy, pandas, matplotlib)
4.  Key project files and directories
5.  Paper environment doctor (paper_env_doctor)
"""

import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

PASS = 0
WARN = 0
FAIL = 0


def check(label: str, ok: bool, detail: str = "", critical: bool = False) -> bool:
    global PASS, WARN, FAIL
    if ok:
        PASS += 1
        print(f"  [PASS] {label}")
        return True
    elif critical:
        FAIL += 1
        print(f"  [FAIL] {label} — {detail}")
        return False
    else:
        WARN += 1
        print(f"  [WARN] {label} — {detail}")
        return False


def section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


# ─── 1. Python ───────────────────────────────────────────────
section("1. Python Runtime")

v = sys.version_info
check("Python 3.10+", v >= (3, 10),
      f"Found {v.major}.{v.minor}.{v.micro}", critical=True)
print(f"  [INFO] Executable: {sys.executable}")
print(f"  [INFO] Version:    {sys.version.split()[0]}")


# ─── 2. mmos package ─────────────────────────────────────────
section("2. mmos Package Integrity")

required_modules = [
    ("mmos/__init__.py", "core package"),
    ("mmos/cli/main.py", "CLI entry point"),
    ("mmos/kernel/jsonio.py", "JSON I/O"),
    ("mmos/kernel/paths.py", "path resolution"),
    ("mmos/kernel/events.py", "event logging"),
    ("mmos/kernel/hashing.py", "file hashing"),
    ("mmos/ingestion/document_ingestor.py", "document ingestion"),
    ("mmos/problem_graph/parser.py", "problem parser"),
    ("mmos/academic_research_engine/search_orchestrator.py", "academic search engine"),
    ("mmos/academic_research_engine/coverage_checker.py", "coverage checker"),
    ("mmos/problem_signature/extractor.py", "problem signature extractor"),
    ("mmos/method_plan/synthesizer.py", "method plan synthesizer"),
    ("mmos/semantic_audit/auditor.py", "semantic auditor"),
    ("mmos/claim_evidence/checker.py", "claim evidence"),
    ("mmos/paper_latex/latex.py", "LaTeX builder"),
    ("mmos/paper_excellence/checks.py", "paper checks"),
    ("mmos/paper_excellence/evidence_engine.py", "evidence engine"),
    ("mmos/gates/final_gate.py", "final gate"),
    ("mmos/gates/first_prize_gate.py", "first prize gate"),
    ("mmos/contest_commander/autopilot.py", "autopilot"),
    ("mmos/quality_oracle/oracle.py", "quality oracle"),
    ("mmos/tournament/solver_tournament.py", "solver tournament"),
    ("scripts/mmtool.py", "CLI tool"),
]

for rel_path, desc in required_modules:
    p = ROOT / rel_path
    check(f"{rel_path}", p.exists(), f"File missing: {rel_path}", critical=("/mmtool.py" in rel_path or "mmos/cli/main.py" == rel_path))


# ─── 3. Python imports ──────────────────────────────────────
section("3. Python Package Imports")

try:
    from mmos.kernel.jsonio import read_json, write_json
    from mmos.kernel.paths import OSPaths
    from mmos.kernel.events import now_iso
    from mmos.kernel.hashing import sha256_file
    check("mmos.kernel (jsonio, paths, events, hashing)", True)
except Exception as e:
    check("mmos.kernel", False, str(e), critical=True)

try:
    from mmos.paper_latex.latex import paper_env_doctor
    check("mmos.paper_latex.latex (paper_env_doctor)", True)
except Exception as e:
    check("mmos.paper_latex", False, str(e), critical=True)

try:
    from mmos.ingestion.document_ingestor import build_problem_corpus
    from mmos.problem_graph.parser import build_problem_graph
    check("mmos.ingestion + problem_graph", True)
except Exception as e:
    check("mmos.ingestion/probleom_graph", False, str(e))

try:
    from mmos.academic_research_engine.search_orchestrator import orchestrate_academic_search
    from mmos.problem_signature.extractor import extract_problem_signature
    from mmos.method_plan.synthesizer import synthesize_method_plan
    check("mmos.academic_research_engine + problem_signature + method_plan", True)
except Exception as e:
    check("mmos.academic_research_engine", False, str(e))


# ─── 4. LaTeX toolchain ─────────────────────────────────────
section("4. LaTeX Toolchain (for PDF generation)")

xelatex = shutil.which("xelatex")
check("xelatex", xelatex is not None,
      "Install TeX Live (https://tug.org/texlive/) or MiKTeX", critical=True)
if xelatex:
    print(f"  [INFO] Path: {xelatex}")

latexmk = shutil.which("latexmk")
check("latexmk (recommended)", latexmk is not None,
      "Without latexmk, falls back to direct xelatex twice mode")

pdftotext = shutil.which("pdftotext")
check("pdftotext (required for PDF text check)", pdftotext is not None,
      "Install via TeX Live or xpdf tools", critical=True)
if pdftotext:
    print(f"  [INFO] Path: {pdftotext}")

tectonic = shutil.which("tectonic")
if tectonic:
    print(f"  [INFO] tectonic also available (alternative engine)")


# ─── 5. Scientific computing stack ──────────────────────────
section("5. Python Scientific Computing Stack")

libs = ["numpy", "scipy", "pandas", "matplotlib", "networkx"]
for lib in libs:
    try:
        __import__(lib)
        check(lib, True)
    except ImportError:
        check(lib, False, f"pip install {lib} --break-system-packages")


# ─── 6. Key directories ─────────────────────────────────────
section("6. Key Project Directories")

dirs = [
    ("mmos/", "Python package"),
    ("scripts/", "CLI scripts"),
    ("mmos/academic_research_engine/", "academic research engine (v7.2 control-plane compatible)"),
    ("mmos/problem_understanding/", "problem understanding engine (v7.2 control-plane compatible)"),
    ("mmos/problem_signature/", "problem signature compatibility wrapper (v7.2 control-plane compatible)"),
    ("mmos/method_plan/", "method plan (v7.2 control-plane compatible)"),
    ("knowledge_packs/", "knowledge packs"),
    ("schemas/", "JSON Schemas"),
    ("contracts/", "OS contracts"),
    ("templates/", "case/contract templates"),
    ("paper_templates/cumcm_gold/", "LaTeX template"),
    ("cases/", "competition cases"),
    ("docs/", "documentation"),
    (".agent/", "Agent control plane"),
    (".agent/protocols/", "Agent protocols"),
]
for rel, desc in dirs:
    p = ROOT / rel
    check(desc, p.is_dir(), f"Directory missing: {rel}")


# ─── 7. paper_env_doctor ────────────────────────────────────
section("7. Paper Environment Doctor (full diagnostic)")

try:
    result = paper_env_doctor(ROOT)
    status = result.get("status", "unknown")
    compile_mode = result.get("compile_mode", "unknown")
    blockers = result.get("blockers", [])
    warnings_list = result.get("warnings", [])

    print(f"  [INFO] Status:        {status}")
    print(f"  [INFO] Compile mode:  {compile_mode}")

    if blockers:
        for b in blockers:
            print(f"  [BLOCK] {b.get('code')}: {b.get('message')}")

    if warnings_list:
        for w in warnings_list:
            print(f"  [WARN]  {w.get('code')}: {w.get('fallback', '')}")

    for name, info in result.get("checks", {}).items():
        available = info.get("available", False)
        check(f"  {name}", available,
              f"Required for: {info.get('required_for_pdf', info.get('required_for_pdf_text_check', 'N/A'))}")

    check("paper_env_doctor.run", status != "blocked",
          "Cannot generate PDF without LaTeX engine", critical=True)

except Exception as e:
    check("paper_env_doctor", False, str(e), critical=True)


# ─── 8. Summary ─────────────────────────────────────────────
section("8. Summary")

print(f"  Passed:  {PASS}")
print(f"  Warnings:{WARN}")
print(f"  Failed:  {FAIL}")
print()

if FAIL == 0 and WARN == 0:
    print("  All checks passed. Environment is fully ready!")
elif FAIL == 0:
    print("  Environment is operational with warnings. Review warnings above.")
else:
    print("  Some critical checks failed. Fix the [FAIL] items above before running the OS.")

print()
