@echo off
chcp 65001 >nul
echo ============================================================
echo   MM-AI OS v6.2.0 Environment Setup
echo ============================================================
echo.

echo [1/4] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+ from https://python.org
    echo         Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
python --version
echo [OK] Python found.
echo.

echo [2/4] Installing Python scientific stack...
pip install numpy scipy pandas matplotlib networkx --break-system-packages 2>nul
if %errorlevel% neq 0 (
    rem Fallback: try without --break-system-packages for older pip
    pip install numpy scipy pandas matplotlib networkx
)
echo [OK] Scientific stack installed (or already present).
echo.

echo [3/4] Checking LaTeX toolchain...
where xelatex >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] xelatex not found in PATH.
    echo           To generate contest PDFs, install TeX Live from:
    echo           https://tug.org/texlive/
    echo           Or MiKTeX from: https://miktex.org/
    echo           After installation, ensure xelatex.exe is in PATH.
) else (
    xelatex --version 2>nul | findstr /i "XeTeX"
    echo [OK] xelatex found.
)

where pdftotext >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] pdftotext not found in PATH.
    echo           Required for PDF text verification. Included in TeX Live or xpdf tools.
) else (
    echo [OK] pdftotext found.
)

where latexmk >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO]    latexmk not found. Will use direct xelatex twice mode (degraded).
) else (
    echo [OK] latexmk found (optimal compilation mode).
)
echo.

echo [4/4] Verifying mmos package import...
python -c "from mmos.kernel.jsonio import read_json, write_json; from mmos.kernel.paths import OSPaths; from mmos.kernel.events import now_iso; print('mmos kernel: OK')"
if %errorlevel% neq 0 (
    echo [ERROR] mmos package import failed.
    echo         Make sure you are running this script from the project root directory
    echo         (where mmos/ and scripts/ folders are located).
    pause
    exit /b 1
)
echo [OK] mmos package imports successfully.
echo.

echo ============================================================
echo   Environment check complete!
echo.
echo   Next steps:
echo     python setup_verify.py
echo     python scripts\mmtool.py paper-env-doctor .
echo ============================================================
pause
