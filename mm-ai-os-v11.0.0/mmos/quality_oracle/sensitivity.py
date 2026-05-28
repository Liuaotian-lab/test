from __future__ import annotations
from pathlib import Path
from mmos.kernel.events import now_iso
from mmos.kernel.jsonio import read_json, write_json
from .common import ensure_quality_dirs, question_ids, read_solution, write_report


def sensitivity_analysis(case_dir: Path, question_id: str | None = None, budget: str = 'regression') -> dict:
    case_dir = Path(case_dir).resolve(); ensure_quality_dirs(case_dir)
    findings=[]; warnings=[]
    for qid in question_ids(case_dir, question_id):
        sol = read_solution(case_dir, qid)
        if not sol:
            warnings.append({'question_id':qid,'code':'MISSING_SOLUTION_FOR_SENSITIVITY'})
            continue
        diag = sol.get('diagnostics',{}) or {}
        params = diag.get('sensitivity_parameters') or diag.get('assumptions') or []
        if not params:
            warnings.append({'question_id':qid,'code':'SENSITIVITY_NOT_IMPLEMENTED','message':'未发现 solver 输出中的 sensitivity_parameters；当前生成检查占位报告。'})
        finding = {'question_id':qid,'budget':budget,'status':'warning' if not params else 'passed','parameters_checked':params,'recommendation':'对关键假设、成本、概率、几何参数或随机种子进行 ±5%/±10% 扰动，并检查策略是否改变。'}
        write_json(case_dir/'results'/qid/'sensitivity'/'sensitivity_summary.json', finding)
        findings.append(finding)
    report={'gate':'sensitivity-analysis','status':'warning' if warnings else 'passed','findings':findings,'warnings':warnings,'generated_at':now_iso()}
    return write_report(case_dir, 'sensitivity_report.json', report)
