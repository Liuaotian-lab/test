from __future__ import annotations
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from mmos.kernel.events import now_iso
from mmos.kernel.hashing import sha256_file
from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.paths import resolve_case_path
from mmos.gates.final_gate import final_gate_check


def register_output_draft(case_dir: Path, accept: bool = True) -> dict:
    case_dir=Path(case_dir).resolve()
    draft=read_json(case_dir/'registry'/'outputs_registry.draft.json', None)
    if not draft:
        return {'status':'failed','code':'MISSING_OUTPUTS_REGISTRY_DRAFT'}
    outputs = draft.get('outputs', []) if isinstance(draft, dict) else []
    if not outputs:
        return {'status':'failed','code':'EMPTY_OUTPUTS_REGISTRY_DRAFT'}
    if accept:
        write_json(case_dir/'registry'/'outputs_registry.json', draft)
    return {'status':'ok','accepted':accept,'outputs':len(outputs)}


def _safe_submitted_target(case_dir: Path, submitted: Path, source: Path) -> Path:
    """Preserve source-relative paths to prevent cross-question filename collisions."""
    rel = source.resolve().relative_to(case_dir.resolve())
    if rel.parts and rel.parts[0] == 'final_outputs':
        # Keep files already under final_outputs in place.
        return source
    return submitted / rel


def output_build(case_dir: Path, all_required: bool = True) -> dict:
    case_dir=Path(case_dir).resolve()
    reg=read_json(case_dir/'registry'/'outputs_registry.json', {'outputs': []}) or {'outputs': []}
    submitted=case_dir/'final_outputs'/'submitted_files'; submitted.mkdir(parents=True, exist_ok=True)
    built=[]; warnings=[]; failures=[]; seen_targets={}; submitted_entries=[]
    outputs = reg.get('outputs', []) if isinstance(reg, dict) else []
    # v7.5: make output-build idempotent. After a previous build, the registry
    # may contain both original source artifacts and their submitted mirrors under
    # final_outputs/submitted_files/<source-rel>. Keep the source entry as the
    # canonical input and ignore the generated mirror when the source still exists.
    submitted_prefix = Path('final_outputs') / 'submitted_files'
    normalized_outputs = []
    for out in outputs:
        rel = out.get('path') if isinstance(out, dict) else None
        if rel:
            rel_path = Path(rel)
            try:
                source_rel = rel_path.relative_to(submitted_prefix)
            except ValueError:
                source_rel = None
            if source_rel is not None and (case_dir / source_rel).exists():
                continue
        normalized_outputs.append(out)
    outputs = normalized_outputs
    if not outputs:
        failures.append({'code':'EMPTY_OUTPUT_REGISTRY'})
    for out in outputs:
        rel = out.get('path')
        if not rel:
            failures.append({'code':'OUTPUT_WITHOUT_PATH','output':out})
            continue
        try:
            p=resolve_case_path(case_dir, rel)
        except ValueError as exc:
            failures.append({'code':'SOURCE_OUTPUT_PATH_ESCAPES_CASE','path':rel,'message':str(exc)})
            continue
        if not p.exists():
            if out.get('required') or all_required:
                failures.append({'code':'SOURCE_OUTPUT_MISSING','path':rel})
            else:
                warnings.append({'code':'OPTIONAL_SOURCE_OUTPUT_MISSING','path':rel})
            continue
        try:
            target=_safe_submitted_target(case_dir, submitted, p)
            target_rel = str(target.relative_to(case_dir))
        except Exception:
            failures.append({'code':'TARGET_ESCAPES_CASE','source':rel,'target':str(target)})
            continue
        prev = seen_targets.get(target_rel)
        if prev and prev != rel:
            failures.append({'code':'SUBMITTED_TARGET_COLLISION','target':target_rel,'sources':[prev, rel]})
            continue
        seen_targets[target_rel]=rel
        entry = dict(out)
        entry['path'] = target_rel
        entry['required'] = True
        entry['sha256'] = sha256_file(target) if target.exists() and target.resolve() == p.resolve() else sha256_file(p)
        if target.resolve() == p.resolve():
            built.append({'path':target_rel,'action':'already_submitted','sha256':sha256_file(target)})
            submitted_entries.append(entry)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(p.read_bytes())
        entry['sha256'] = sha256_file(target)
        built.append({'source':rel,'target':target_rel,'sha256':sha256_file(target)})
        submitted_entries.append(entry)
    # Promote submitted copies into the accepted output registry so output-validate has
    # explicit required deliverables rather than only optional intermediate artifacts.
    if submitted_entries:
        by_path = {o.get('path'): o for o in outputs if o.get('path')}
        for entry in submitted_entries:
            by_path[entry['path']] = entry
        reg['outputs'] = list(by_path.values())
        write_json(case_dir/'registry'/'outputs_registry.json', reg)
    manifest={'case_id':case_dir.name,'built_at':now_iso(),'files':built,'warnings':warnings,'failures':failures}
    write_json(case_dir/'final_outputs'/'output_manifest.json', manifest)
    return {'status':'failed' if failures else ('warning' if warnings else 'ok'),'built':built,'warnings':warnings,'failures':failures,'manifest':'final_outputs/output_manifest.json'}


def package_case(case_dir: Path, strict_warnings: bool = True) -> dict:
    case_dir=Path(case_dir).resolve()
    final_gate = final_gate_check(case_dir, strict_warnings=strict_warnings, write=True)
    if final_gate.get('status') != 'passed':
        return {
            'status':'failed',
            'code':'FINAL_GATE_NOT_PASSED',
            'final_allowed':False,
            'final_gate_report':'final_outputs/final_gate_check.json',
            'failures':final_gate.get('failures', []),
            'warnings':final_gate.get('warnings', []),
        }
    package_dir=case_dir/'package'; package_dir.mkdir(parents=True, exist_ok=True)
    zip_path=package_dir/'final_submission.zip'
    include_roots=['final_outputs','reports','evidence','quality','.agent/gate_reports','.agent/solver_verify_reports','.agent/red_team_reports']
    files=[]
    with ZipFile(zip_path, 'w', ZIP_DEFLATED) as z:
        for relroot in include_roots:
            root=case_dir/relroot
            if not root.exists():
                continue
            for p in sorted(root.rglob('*')):
                if p.is_file():
                    arc=str(p.relative_to(case_dir))
                    z.write(p, arc)
                    files.append({'path':arc,'sha256':sha256_file(p),'size_bytes':p.stat().st_size})
    manifest={'case_id':case_dir.name,'created_at':now_iso(),'zip_path':str(zip_path.relative_to(case_dir)),'files':files,'zip_sha256':sha256_file(zip_path),'final_gate_report':'final_outputs/final_gate_check.json'}
    write_json(package_dir/'package_manifest.json', manifest)
    return {'status':'ok','zip_path':str(zip_path),'file_count':len(files),'manifest':'package/package_manifest.json','final_gate_report':'final_outputs/final_gate_check.json'}
