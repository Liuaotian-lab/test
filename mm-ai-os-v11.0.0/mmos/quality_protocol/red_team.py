from __future__ import annotations
from pathlib import Path
from mmos.modeling_os.common import write_json, read_json, solution_files, status_from, rel_to_case
from .review import _issue


def red_team_gate(case_dir: Path, all_questions: bool=True) -> dict:
    case_dir=Path(case_dir).resolve(); issues=[]
    for sol in solution_files(case_dir):
        data=read_json(sol,{}) or {}
        qid=data.get('question_id')
        if data.get('optimal') is True and data.get('quality_level') in {'heuristic_feasible','simulation_estimate','approximate','exploratory','local_optimal'}:
            issues.append(_issue(f'issue_{len(issues)+1:03d}','blocking','false_optimality_claim','Non-certified result claims optimal=true.',[rel_to_case(case_dir, sol)],'Downgrade quality_level/optimal flag or provide certificate.',qid))
        if data.get('data_source')=='demo_data' and data.get('scope')=='real':
            issues.append(_issue(f'issue_{len(issues)+1:03d}','blocking','demo_data_as_real','Demo data is marked as real scope.',[rel_to_case(case_dir, sol)],'Use real data or downgrade scope/data_source.',qid))
    blocking=[i for i in issues if i['severity']=='blocking']
    report={'status':status_from(blocking,[]),'issues':issues,'blocking_issue_count':len(blocking),'final_allowed':len(blocking)==0}
    write_json(case_dir/'reports'/'red_team_gate_report.json', report)
    return report
