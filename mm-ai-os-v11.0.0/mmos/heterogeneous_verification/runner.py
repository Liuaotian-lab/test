from __future__ import annotations
from pathlib import Path
from typing import Any

from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from mmos.kernel_gates.common import required_questions, status_from


def _qids(case_dir: Path) -> list[str]:
    comp=read_json(Path(case_dir)/'workspace'/'dynamic_protocols'/'official'/'compiled_protocol.json', {}) or {}
    return sorted((comp.get('question_contracts') or {}).keys()) or required_questions(Path(case_dir)) or ['Q1']


def _metric_value(sol: dict[str, Any]) -> float | None:
    metrics=sol.get('metrics') if isinstance(sol.get('metrics'),dict) else {}
    for k in ['objective','value','score','annual_power','output_power','unit_power']:
        v=metrics.get(k)
        if isinstance(v,(int,float)):
            return float(v)
    return None


def independent_solver_synthesize(case_dir: Path, question_id: str | None = None, all_questions: bool = False) -> dict[str, Any]:
    case_dir=Path(case_dir); qids=[question_id] if question_id else _qids(case_dir)
    protocols=[]
    for qid in qids:
        proto={'question_id':qid,'independent_strategy':'heterogeneous_recompute_or_invariant_check','required_difference_from_primary':['alternate_metric_path','invariant_or_boundary_probe'],'tolerance':{'relative':0.05,'absolute':1e-6}}
        protocols.append(proto)
        write_json(case_dir/'results'/qid/'reports'/'independent_solver_protocol.json', proto)
    report={'command':'independent-solver-synthesize','status':'passed','protocols':protocols,'generated_at':now_iso()}
    write_json(case_dir/'quality'/'independent_solver_synthesize_report.json', report)
    return report


def heterogeneous_verify(case_dir: Path, question_id: str | None = None, all_questions: bool = False) -> dict[str, Any]:
    case_dir=Path(case_dir); qids=[question_id] if question_id else _qids(case_dir)
    failures=[]; warnings=[]; reports=[]
    for qid in qids:
        sol=read_json(case_dir/'results'/qid/'outputs'/'solution_real.json', {}) or {}
        if not sol:
            warnings.append({'code':'NO_PRIMARY_SOLUTION_FOR_HETEROGENEOUS_VERIFY','question_id':qid})
            reports.append({'question_id':qid,'status':'warning','reason':'missing_solution'})
            continue
        v=_metric_value(sol)
        diag=sol.get('diagnostics') if isinstance(sol.get('diagnostics'),dict) else {}
        alt=diag.get('independent_metric')
        if isinstance(alt,(int,float)) and v is not None:
            diff=abs(float(alt)-v); rel=diff/(abs(v)+1e-12)
            status='passed' if rel <= 0.05 else 'failed'
            if status=='failed':
                failures.append({'code':'HETEROGENEOUS_VERIFY_DISCREPANCY','question_id':qid,'primary':v,'independent':alt,'relative_diff':rel})
            reports.append({'question_id':qid,'status':status,'primary_metric':v,'independent_metric':alt,'relative_diff':rel})
        else:
            # invariant fallback: valid verified solution with constraints checked is acceptable but medium-strength.
            if (diag.get('constraints_checked') is True or sol.get('violation_count') == 0):
                warnings.append({'code':'HETEROGENEOUS_VERIFY_USED_INVARIANT_FALLBACK','question_id':qid})
                reports.append({'question_id':qid,'status':'warning','mode':'invariant_fallback'})
            else:
                failures.append({'code':'HETEROGENEOUS_VERIFY_NO_ALTERNATE_EVIDENCE','question_id':qid})
                reports.append({'question_id':qid,'status':'failed','reason':'no_alternate_evidence'})
        write_json(case_dir/'results'/qid/'reports'/'heterogeneous_verification_report.json', reports[-1])
    report={'gate':'heterogeneous-verify','status':status_from(failures,warnings),'question_reports':reports,'failures':failures,'warnings':warnings,'generated_at':now_iso()}
    write_json(case_dir/'quality'/'heterogeneous_verify_report.json', report)
    return report


def discrepancy_report(case_dir: Path, question_id: str | None = None, all_questions: bool = False) -> dict[str, Any]:
    case_dir=Path(case_dir)
    hv=read_json(case_dir/'quality'/'heterogeneous_verify_report.json', {}) or heterogeneous_verify(case_dir, question_id=question_id, all_questions=all_questions)
    discrepancies=[]
    for f in hv.get('failures') or []:
        if 'DISCREPANCY' in f.get('code',''):
            discrepancies.append(f)
    report={'status':'failed' if discrepancies else ('warning' if hv.get('warnings') else 'passed'),'discrepancy_count':len(discrepancies),'discrepancies':discrepancies,'source_status':hv.get('status'),'generated_at':now_iso()}
    write_json(case_dir/'quality'/'discrepancy_report.json', report)
    return report
