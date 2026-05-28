#!/usr/bin/env python3
from pathlib import Path
import json, sys

ROOT = Path(__file__).resolve().parents[1]
version = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
codename_path = ROOT / "VERSION_CODENAME"
codename = codename_path.read_text(encoding="utf-8").strip() if codename_path.exists() else ""
errors = []

init_text = (ROOT / "mmos" / "__init__.py").read_text(encoding="utf-8")
if f'__version__ = "{version}"' not in init_text:
    errors.append("mmos/__init__.py version mismatch")
if codename and f'__version_codename__ = "{codename}"' not in init_text:
    errors.append("mmos/__init__.py codename mismatch")

manifest = json.loads((ROOT / "os_manifest.json").read_text(encoding="utf-8"))
if manifest.get("version") != version:
    errors.append("os_manifest.json version mismatch")
if codename and manifest.get("codename") != codename:
    errors.append("os_manifest.json codename mismatch")

contract = json.loads((ROOT / "contracts" / "os_contract.json").read_text(encoding="utf-8"))
if contract.get("version") != version and contract.get("schema_version") != version:
    errors.append("contracts/os_contract.json version mismatch")

readme = (ROOT / "README.md").read_text(encoding="utf-8")
if version not in readme:
    errors.append("README.md does not contain current version")
if codename and codename not in readme:
    errors.append("README.md does not contain current codename")

if errors:
    for e in errors:
        print("FAIL:", e)
    sys.exit(1)
suffix = f"-{codename}" if codename else ""
print(f"OK: version consistency verified: {version}{suffix}")
