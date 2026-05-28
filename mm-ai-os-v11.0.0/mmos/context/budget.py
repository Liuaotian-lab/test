from __future__ import annotations
from pathlib import Path
from mmos.modeling_os.common import write_json, read_json, status_from, question_ids

DEFAULT_BUDGET={'max_context_files':8,'max_total_lines':2000,'max_skill_files':3,'max_log_lines_in_context':200}


def context_build(case_dir: Path, task: str) -> dict:
    case_dir=Path(case_dir).resolve()
    ids=question_ids(case_dir)
    summary=['# Case State Summary','','## Status','METHOD_PLANNED','','## Active Questions']
    summary += [f'- {qid}: pending modeling workflow' for qid in ids] or ['- None detected']
    summary += ['', '## Official Artifacts']
    for p in sorted((case_dir/'workspace').rglob('official/*')) if (case_dir/'workspace').exists() else []:
        if p.is_file(): summary.append(f'- {p.relative_to(case_dir).as_posix()}')
    summary += ['', '## Pending Gates','- validator-test','- solver-verify','- evidence-check','','## Known Risks','- Generated context requires task-specific review.']
    state=case_dir/'state'/'case_state_summary.md'; state.parent.mkdir(parents=True, exist_ok=True); state.write_text('\n'.join(summary[:200])+'\n', encoding='utf-8')
    active = (
        '# Active Task Context\n\n'
        '## Task\n' + str(task) + '\n\n'
        '## Allowed Files\n'
        '- engineering/questions/**\n'
        '- engineering/results/**\n'
        '- workspace/**/candidate/**\n'
        '- .agent/run_reports/**\n\n'
        '## Forbidden Files\n'
        '- workspace/**/official/**\n'
        '- final_outputs/**\n'
        '- package/**\n'
        '- schemas/**\n\n'
        '## Required Inputs\n'
        '- contracts/questions/\n'
        '- workspace/routing/official/problem_routing.json\n\n'
        '## Acceptance\n'
        '- validator-test passes\n'
        '- negative-test passes\n'
        '- solver-verify --strict passes\n'
    )
    act=case_dir/'.agent'/'context'/'active_task_context.md'; act.parent.mkdir(parents=True, exist_ok=True); act.write_text(active, encoding='utf-8')
    manifest={'task':task,'loaded_files':[str(state.relative_to(case_dir)),str(act.relative_to(case_dir))], 'budget':DEFAULT_BUDGET}
    write_json(case_dir/'.agent'/'context'/'loaded_files_manifest.json', manifest)
    report=context_check(case_dir)
    return {'status':report['status'],'outputs':[str(state.relative_to(case_dir)),str(act.relative_to(case_dir)),'.agent/context/loaded_files_manifest.json'],'context_check':report}


def context_check(case_dir: Path) -> dict:
    case_dir=Path(case_dir).resolve(); failures=[]; warnings=[]
    manifest=read_json(case_dir/'.agent'/'context'/'loaded_files_manifest.json', {}) or {}
    budget=manifest.get('budget') or DEFAULT_BUDGET
    loaded=manifest.get('loaded_files') or []
    total=0; files=[]
    for rel in loaded:
        p=case_dir/rel
        if p.exists() and p.is_file():
            lines=len(p.read_text(encoding='utf-8', errors='replace').splitlines()); total+=lines; files.append({'path':rel,'lines':lines})
        else:
            warnings.append({'code':'CONTEXT_FILE_MISSING','path':rel})
    if len(files)>int(budget.get('max_context_files',8)):
        failures.append({'code':'CONTEXT_FILE_BUDGET_EXCEEDED','used':len(files),'max':budget.get('max_context_files')})
    if total>int(budget.get('max_total_lines',2000)):
        failures.append({'code':'CONTEXT_LINE_BUDGET_EXCEEDED','used':total,'max':budget.get('max_total_lines')})
    report={'status':status_from(failures,warnings),'used_files':len(files),'used_total_lines':total,'files':files,'failures':failures,'warnings':warnings,'budget':budget}
    write_json(case_dir/'.agent'/'context'/'context_budget_report.json', report)
    return report


def context_compact(case_dir: Path) -> dict:
    case_dir=Path(case_dir).resolve(); p=case_dir/'state'/'case_state_summary.md'
    if not p.exists():
        return context_build(case_dir, task='compact')
    lines=p.read_text(encoding='utf-8', errors='replace').splitlines()[:200]
    p.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return context_check(case_dir)
