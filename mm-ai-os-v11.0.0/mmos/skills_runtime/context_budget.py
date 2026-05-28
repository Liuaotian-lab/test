from __future__ import annotations
from pathlib import Path
from mmos.modeling_os.common import status_from


def evaluate_context_budget(root: Path, manifest: dict) -> dict:
    budget=manifest.get('context_budget') or {}
    max_files=int(budget.get('max_files', 8))
    max_total_lines=int(budget.get('max_total_lines', 2000))
    inputs=manifest.get('inputs') or []
    loaded=[]; failures=[]; total=0
    for rel in inputs:
        p=Path(root)/rel
        if p.exists() and p.is_file():
            lines=p.read_text(encoding='utf-8', errors='replace').splitlines()
            loaded.append({'path':rel,'lines':len(lines)})
            total+=len(lines)
    if len(loaded)>max_files:
        failures.append({'code':'CONTEXT_FILE_BUDGET_EXCEEDED','used':len(loaded),'max':max_files})
    if total>max_total_lines:
        failures.append({'code':'CONTEXT_LINE_BUDGET_EXCEEDED','used':total,'max':max_total_lines})
    return {'status':status_from(failures,[]),'max_files':max_files,'used_files':len(loaded),'max_total_lines':max_total_lines,'used_total_lines':total,'loaded_files':loaded,'failures':failures}
