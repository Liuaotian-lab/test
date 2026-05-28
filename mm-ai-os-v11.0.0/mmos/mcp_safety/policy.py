from __future__ import annotations
from pathlib import Path
from fnmatch import fnmatch
from mmos.modeling_os.common import write_json, now_iso, status_from

TOOL_CLASSES={'read_only','candidate_write','sandbox_compute','external_search','dangerous_write','secret_access'}
DENY_WRITE=['workspace/**/official/**','final_outputs/**','package/**','contracts/**','schemas/**','.env','secrets/**']
ALLOW_CANDIDATE=['workspace/**/candidate/**','.agent/tool_reports/**']


def evaluate_mcp_safe_call(case_dir: Path, *, tool_class: str, target: str | None=None, query: str | None=None, source_url: str | None=None, used_for: str='method_advisory') -> dict:
    case_dir=Path(case_dir).resolve(); failures=[]; warnings=[]; provenance=None; allowed=False; reason=''
    if tool_class not in TOOL_CLASSES:
        failures.append({'code':'UNKNOWN_TOOL_CLASS','tool_class':tool_class}); reason='unknown tool class'
    elif tool_class=='secret_access':
        failures.append({'code':'SECRET_ACCESS_FORBIDDEN'}); reason='secret access is forbidden'
    elif tool_class=='dangerous_write':
        failures.append({'code':'DANGEROUS_WRITE_DENIED'}); reason='dangerous write is denied by default'
    elif tool_class=='candidate_write':
        rel=(target or '').lstrip('./')
        if any(fnmatch(rel, pat) for pat in DENY_WRITE) or not any(fnmatch(rel, pat) for pat in ALLOW_CANDIDATE):
            failures.append({'code':'MCP_WRITE_TARGET_DENIED','target':target}); reason='write target must be candidate/tool report path'
        else:
            allowed=True; reason='candidate write permitted'
    elif tool_class=='external_search':
        if not (query and source_url):
            failures.append({'code':'MCP_EXTERNAL_SEARCH_PROVENANCE_REQUIRED'}); reason='external search requires query and source_url'
        else:
            allowed=True; reason='external search permitted with provenance'
            provenance={'tool':'external_search','query':query,'timestamp':now_iso(),'source_url':source_url,'used_for':used_for,'promoted_to_official':False}
    else:
        allowed=True; reason=f'{tool_class} permitted'
    report={'status':status_from(failures,warnings),'tool_class':tool_class,'target':target,'allowed':allowed and not failures,'reason':reason,'failures':failures,'warnings':warnings,'provenance':provenance}
    write_json(case_dir/'.agent'/'tool_reports'/f'mcp_safe_{tool_class}.json', report)
    if provenance:
        write_json(case_dir/'.agent'/'tool_reports'/f'mcp_provenance_{tool_class}.json', provenance)
    return report
