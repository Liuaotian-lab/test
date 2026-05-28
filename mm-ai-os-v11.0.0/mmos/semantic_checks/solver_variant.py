from __future__ import annotations
from pathlib import Path
from typing import Any
from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from mmos.quality_oracle.common import registry_questions


def solver_variant_verify(case_dir: Path, question_id: str | None = None, strict: bool = True, write: bool = True) -> dict[str, Any]:
    case_dir=Path(case_dir).resolve(); failures=[]; warnings=[]; reports=[]
    qs=registry_questions(case_dir)
    if question_id: qs=[q for q in qs if (q.get('question_id') or q.get('id'))==question_id]
    for q in qs:
        qid=q.get('question_id') or q.get('id')
        sdir=case_dir/'results'/qid/'solver_runs'
        variants=[]
        for p in sorted(sdir.glob('*.json')):
            if p.name in {'benchmark_report.json'}: continue
            data=read_json(p,{}) or {}
            # either direct variant spec or wrapper
            solver_code=data.get('solver_code_path') or data.get('run_command') or data.get('code_path')
            output_hash=data.get('output_artifact_hash') or data.get('result_hash')
            runtime_log=data.get('runtime_log') or data.get('runtime_log_path')
            ok=bool(solver_code and output_hash and runtime_log)
            if not ok:
                msg={'code':'NON_RUNNABLE_SOLVER_VARIANT','question_id':qid,'variant_file':str(p.relative_to(case_dir)),'missing':[x for x,y in [('solver_code_path/run_command',solver_code),('output_artifact_hash/result_hash',output_hash),('runtime_log',runtime_log)] if not y]}
                if strict: failures.append(msg)
                else: warnings.append(msg)
            variants.append({'file':str(p.relative_to(case_dir)),'runnable':ok})
        if strict and len([v for v in variants if v['runnable']]) < 2:
            failures.append({'code':'INSUFFICIENT_RUNNABLE_SOLVER_VARIANTS','question_id':qid,'count':len([v for v in variants if v['runnable']])})
        reports.append({'question_id':qid,'variants':variants})
    status='failed' if failures else ('warning' if warnings else 'passed')
    report={'gate':'solver-variant-verify','status':status,'strict':strict,'reports':reports,'failures':failures,'warnings':warnings,'generated_at':now_iso()}
    if write:
        write_json(case_dir/'quality'/'solver_variant_verify.json', report)
        write_json(case_dir/'.agent'/'gate_reports'/'solver_variant_verify.json', report)
    return report
