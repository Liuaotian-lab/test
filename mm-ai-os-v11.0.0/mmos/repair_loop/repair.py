from __future__ import annotations
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import read_json, write_json


def repair_plan(case_dir: Path) -> dict[str, Any]:
    case_dir=Path(case_dir).resolve()
    ar=read_json(case_dir/'quality'/'award_readiness.json',{}) or {}
    actions=ar.get('repair_actions') or []
    tasks=[]
    for i, action in enumerate(actions, 1):
        tasks.append({'task_id': f'R{i:02d}', 'action': action, 'severity': 'P1' if i<=3 else 'P2', 'validation': 'rerun award-readiness-check after completing this repair'})
    out={'status':'passed' if tasks else 'warning','case_id':case_dir.name,'current_award_ceiling':ar.get('current_award_ceiling'),'tasks':tasks}
    write_json(case_dir/'workspace'/'repair'/'repair_plan.json', out)
    return out

def repair_task_generate(case_dir: Path) -> dict[str, Any]:
    case_dir=Path(case_dir).resolve(); plan=read_json(case_dir/'workspace'/'repair'/'repair_plan.json',{}) or repair_plan(case_dir)
    out_dir=case_dir/'.agent'/'task_cards'/'repair_round_1'; out_dir.mkdir(parents=True, exist_ok=True)
    for t in plan.get('tasks',[]):
        md=f"""# Repair Task {t['task_id']}\n\n- severity: `{t['severity']}`\n- objective: {t['action']}\n- validation: `{t['validation']}`\n\n## Required Work\n\nModify real contracts, solver/verifier code, paper text, figure manifests, or outputs as needed. Do not satisfy this task by editing reports only.\n"""
        (out_dir/f"{t['task_id']}.md").write_text(md, encoding='utf-8')
    return {'status':'passed','task_dir':str(out_dir),'task_count':len(plan.get('tasks',[]))}
