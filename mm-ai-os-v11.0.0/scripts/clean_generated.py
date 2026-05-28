#!/usr/bin/env python3
from pathlib import Path
import shutil
ROOT = Path(__file__).resolve().parents[1]
for p in list(ROOT.rglob('__pycache__')): shutil.rmtree(p, ignore_errors=True)
for p in list(ROOT.rglob('*.pyc')): p.unlink(missing_ok=True)
print('generated Python caches removed')
