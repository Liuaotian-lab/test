from __future__ import annotations
from pathlib import Path


def _parse_capability(path: Path) -> dict:
    data={'_path':str(path)}; current=None
    for raw in path.read_text(encoding='utf-8').splitlines():
        line=raw.rstrip()
        if not line or line.lstrip().startswith('#'):
            continue
        if line.startswith('  - ') and current:
            data.setdefault(current, []).append(line[4:].strip())
        elif ':' in line and not line.startswith(' '):
            key, val=line.split(':',1); key=key.strip(); val=val.strip()
            current=key
            if val and val != '>': data[key]=val
            elif val == '>': data[key]=''
            else: data[key]=[]
        elif current and isinstance(data.get(current), str):
            data[current]=(data[current] + ' ' + line.strip()).strip()
    return data


def capability_list(root: Path) -> dict:
    base=Path(root)/'capabilities'; caps=[]
    if base.exists():
        for p in sorted(base.glob('*.yaml')):
            c=_parse_capability(p); caps.append({'capability_id':c.get('capability_id') or p.stem,'purpose':c.get('purpose','')})
    return {'status':'passed','capability_count':len(caps),'capabilities':caps}


def capability_show(root: Path, capability_id: str) -> dict:
    path=Path(root)/'capabilities'/f'{capability_id}.yaml'
    if not path.exists():
        return {'status':'failed','failures':[{'code':'CAPABILITY_NOT_FOUND','capability_id':capability_id}]}
    return {'status':'passed','capability':_parse_capability(path)}
