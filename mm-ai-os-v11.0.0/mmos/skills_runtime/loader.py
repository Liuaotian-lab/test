from __future__ import annotations
from pathlib import Path
from mmos.modeling_os.common import read_json
from .manifest import load_manifest, validate_manifest


def list_skills(root: Path) -> dict:
    skills=[]
    base=Path(root)/'skills'
    if base.exists():
        for p in sorted(base.iterdir()):
            if p.is_dir() and (p/'manifest.json').exists():
                m=read_json(p/'manifest.json', {}) or {}
                skills.append({'skill_id':m.get('skill_id') or p.name,'version':m.get('version'),'purpose':m.get('purpose')})
    return {'status':'passed','skills':skills,'skill_count':len(skills)}


def show_skill(root: Path, skill_id: str) -> dict:
    m=load_manifest(root, skill_id)
    return {'status':validate_manifest(m)['status'],'manifest':{k:v for k,v in m.items() if not k.startswith('_')},'validation':validate_manifest(m)}
