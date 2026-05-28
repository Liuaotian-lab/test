from __future__ import annotations
from pathlib import Path
from fnmatch import fnmatch
from mmos.modeling_os.common import read_json, status_from

REQUIRED_MANIFEST_FIELDS = ['skill_id','version','purpose','activation','context_budget','inputs','allowed_write_paths','required_outputs','required_gates']
DENY_WRITE_PATTERNS = ['workspace/**/official/**','final_outputs/**','package/**','contracts/**','schemas/**','.env','secrets/**']


def load_manifest(root: Path, skill_id: str) -> dict:
    path=Path(root)/'skills'/skill_id/'manifest.json'
    data=read_json(path, None)
    if data is None:
        raise FileNotFoundError(f'skill manifest not found: {path}')
    data['_manifest_path']=str(path)
    return data


def validate_manifest(manifest: dict) -> dict:
    failures=[]; warnings=[]
    for f in REQUIRED_MANIFEST_FIELDS:
        if f not in manifest:
            failures.append({'code':'SKILL_MANIFEST_FIELD_MISSING','field':f})
    for rel in manifest.get('required_outputs', []) or []:
        for pat in DENY_WRITE_PATTERNS:
            if fnmatch(rel, pat):
                failures.append({'code':'SKILL_REQUIRED_OUTPUT_FORBIDDEN','path':rel,'pattern':pat})
    for patn in manifest.get('allowed_write_paths', []) or []:
        for pat in DENY_WRITE_PATTERNS:
            if fnmatch(patn, pat) or fnmatch(pat, patn):
                failures.append({'code':'SKILL_ALLOWED_WRITE_FORBIDDEN','path':patn,'pattern':pat})
    return {'status':status_from(failures,warnings),'skill_id':manifest.get('skill_id'),'failures':failures,'warnings':warnings}
