from __future__ import annotations
from pathlib import Path
import shutil
import re
from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from mmos.kernel.paths import resolve_case_path
from mmos.core.artifacts import ensure_candidate_official_layout, default_allowed_files_manifest

QUESTION_CONTRACT_FILES = [
    'problem_spec.json','variable_registry.json','objective_registry.json','constraint_registry.json',
    'validation_contract.json','solver_budget.json','missing_information_contract.json','quality_contract.json',
    'tool_contract.json','runtime_contract.json','output_contract.json','evidence_contract.json','report_contract.json',
    'assumption_registry.json','feasibility_registry.json','active_contracts.json','model_candidates.json','extrapolation_risk.json',
    'model_fidelity_contract.json'
]

def _os_root_from_case(case_dir: Path) -> Path:
    p = Path(case_dir).resolve()
    for parent in [p, *p.parents]:
        if (parent / 'templates' / 'contracts_question').exists() and (parent / 'mmos').exists():
            return parent
    # case_dir is normally cases/<id>
    return p.parents[1]

def _copy_with_replacements(src: Path, dst: Path, repl: dict[str,str]) -> None:
    text = src.read_text(encoding='utf-8')
    for k, v in repl.items():
        text = text.replace(k, v)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding='utf-8')


TYPE_ALIASES = {
    'physics_fast_active_reflector': 'geometry_kinematics',
    'physics_fast_active_reflector_shape_adjustment': 'geometry_kinematics',
    'stochastic': 'stochastic_simulation',
    'simulation': 'simulation',
    'optimization': 'generic_optimization',
    'unknown': 'generic_optimization',
}


def _available_question_types(os_root: Path) -> set[str]:
    qtypes = os_root / 'templates' / 'question_types'
    return {p.name for p in qtypes.iterdir() if p.is_dir() and (p / 'run.py').exists()} if qtypes.exists() else set()


def _canonical_question_type(os_root: Path, qtype: str | None) -> str | None:
    if not qtype:
        return None
    qtype = str(qtype).strip()
    available = _available_question_types(os_root)
    if qtype in available:
        return qtype
    alias = TYPE_ALIASES.get(qtype)
    if alias in available:
        return alias
    if qtype.endswith('_field') and qtype in available:
        return qtype
    return None


def _resolve_auto_question_type(case_dir: Path, question_id: str, requested: str | None, old: dict) -> tuple[str, dict]:
    os_root = _os_root_from_case(case_dir)
    available = _available_question_types(os_root)
    resolution = {'requested_type': requested, 'source': 'explicit'}
    if requested and requested != 'auto':
        chosen = _canonical_question_type(os_root, requested)
        if chosen:
            resolution['chosen_type'] = chosen
            if chosen != requested:
                resolution['source'] = 'alias'
            return chosen, resolution
    old_type = old.get('type')
    chosen = _canonical_question_type(os_root, old_type)
    if chosen and old_type not in {None, '', 'unknown', 'auto'}:
        resolution.update({'chosen_type': chosen, 'source': 'registry_existing'})
        return chosen, resolution
    # Use problem signature and method plan for v7 contract context.
    # Try problem signature domain -> question type mapping
    try:
        sig_path = case_dir/'workspace'/'problem_signatures'/'case.signatures.json'
        sig = read_json(sig_path, {}) or {}
        q_sig = sig.get('questions', {}).get(question_id, {})
        domain = (q_sig.get('domain_family') or {}).get('primary', '')
        if domain:
            domain_to_type = {
                'physical_process.thermal_process': 'thermal_reflow_furnace',
                'physical_process.hydraulic_pressure_control': 'hydraulic_pressure_control',
                'operations_research.constrained_optimization': 'generic_optimization',
                'graph_network.graph_theory': 'graph_network',
                'solar_optical.heliostat_field': 'solar_heliostat_field',
                'statistical_decision': 'statistical_decision',
                'stochastic_simulation': 'stochastic_simulation',
            }
            mapped = domain_to_type.get(domain)
            if mapped and mapped in available:
                resolution.update({'chosen_type': mapped, 'source': 'problem_signature_domain', 'domain_family': domain})
                return mapped, resolution
    except Exception:
        pass

    # v7.0: Try method plan for hints
    try:
        plan = read_json(case_dir/'workspace'/'method_plan'/f'{question_id}_method_plan.json', {}) or {}
        primary = plan.get('primary_model')
        if primary:
            mname = str(primary.get('name', '')).lower()
            if 'thermal' in mname and 'thermal_reflow_furnace' in available:
                resolution.update({'chosen_type': 'thermal_reflow_furnace', 'source': 'method_plan_name'})
                return 'thermal_reflow_furnace', resolution
            if 'hydraulic' in mname and 'hydraulic_pressure_control' in available:
                resolution.update({'chosen_type': 'hydraulic_pressure_control', 'source': 'method_plan_name'})
                return 'hydraulic_pressure_control', resolution
    except Exception:
        pass
    graph = read_json(case_dir/'workspace'/'problem_graph.json', {}) or {}
    for q in graph.get('questions', []):
        if q.get('question_id') == question_id:
            chosen = _canonical_question_type(os_root, q.get('type'))
            if chosen:
                resolution.update({'chosen_type': chosen, 'source': 'problem_graph'})
                return chosen, resolution
    fallback = 'generic_optimization' if 'generic_optimization' in available else (sorted(available)[0] if available else 'unknown')
    resolution.update({'chosen_type': fallback, 'source': 'fallback', 'available_types': sorted(available)})
    return fallback, resolution


def activate_all_questions(case_dir: Path, qtype: str = 'auto', required: bool | None = None, force: bool = False) -> dict:
    case_dir = Path(case_dir).resolve(); ensure_case_scaffold(case_dir)
    questions = registry_questions(case_dir)
    if not questions:
        graph = read_json(case_dir/'workspace'/'problem_graph.json', {}) or {}
        questions = graph.get('questions', [])
    if not questions:
        return {'status':'failed', 'code':'NO_QUESTIONS_TO_ACTIVATE'}
    results=[]
    for q in questions:
        qid = q.get('question_id') or q.get('id')
        if not qid:
            continue
        if required is not None:
            q['required'] = required
        results.append(activate_question(case_dir, qid, qtype=qtype, title=q.get('title'), required=q.get('required', True), force=force))
    status = 'failed' if any(r.get('status') == 'failed' for r in results) else 'ok'
    return {'status':status, 'activated_count':len(results), 'results':results}

def ensure_case_scaffold(case_dir: Path) -> dict:
    case_dir = Path(case_dir).resolve()
    dirs = [
        '.agent/task_cards','.agent/protocols','.agent/allowed_files','.agent/gate_reports','.agent/solver_verify_reports','.agent/question_status','.agent/red_team_reports',
        'contracts/global','contracts/questions','data/raw','data/manifest','workspace','registry','engineering/common',
        'engineering/questions','results','runs','final_outputs/submitted_files','evidence/maps','evidence/packs','reports','paper','paper/figures','paper/candidate','paper/official','paper/reports','package','quality','quality/intermediate','quality/tournament','quality/red_team','quality/improvements','workspace/modeling','workspace/problem_understanding/candidate','workspace/problem_understanding/official','workspace/problem_understanding/reports','workspace/academic_search/candidate','workspace/academic_search/official','workspace/academic_search/reports','workspace/method_plan/candidate','workspace/method_plan/official','workspace/method_plan/reports','workspace/artifact_promotions/reports'
    ]
    for d in dirs:
        (case_dir / d).mkdir(parents=True, exist_ok=True)
    # Case-level default files
    defaults = {
        'registry/case_registry.json': {'case_id': case_dir.name, 'status': 'initialized', 'created_at': now_iso(), 'os_version': '7.4.0', 'workflow': 'academic_research_to_cumcm_paper'},
        'registry/questions_registry.json': {'case_id': case_dir.name, 'questions': []},
        'registry/outputs_registry.json': {'case_id': case_dir.name, 'outputs': []},
        'registry/workflow_registry.json': {'case_id': case_dir.name, 'default_workflow': ['contract','preflight','validate','reduced','real','report','solver-verify','output-build','output-validate','evidence','complete'], 'question_workflows': {}},
        '.agent/question_status/case_status.json': {'case_id': case_dir.name, 'overall_status': 'initialized', 'questions': {}, 'last_updated_at': now_iso()},
        '.agent/allowed_files/global_allowed_files.json': {'case_id': case_dir.name, 'default_policy': {'read_allowed': ['data/**','workspace/**/official/**','workspace/**/reports/**','registry/**','contracts/**','engineering/**','results/**','reports/**'], 'write_allowed': ['workspace/**/candidate/**','engineering/questions/**','results/**','runs/**','evidence/**','reports/**','.agent/**','paper/candidate/**'], 'write_forbidden': ['data/raw/**','workspace/**/official/**','final_outputs/**','package/**','paper/official/**']}},
        '.agent/allowed_files/agent_write_policy.json': default_allowed_files_manifest(case_dir.name),
    }
    for rel, data in defaults.items():
        path = case_dir / rel
        if not path.exists():
            write_json(path, data)
    ensure_candidate_official_layout(case_dir)
    global_defaults = {
        'contracts/global/case_contract.json': {'case_id': case_dir.name, 'schema_version': '7.4.0', 'status': 'initialized', 'completion_criteria': ['all_required_questions_complete','required_outputs_validated','evidence_pack_created']},
        'contracts/global/path_policy.json': {'case_id': case_dir.name, 'raw_data_read_only': True, 'path_resolver_required': True, 'case_escape_forbidden': True},
        'contracts/global/quality_policy.json': {'case_id': case_dir.name, 'heuristic_must_disclose': True, 'global_optimal_requires_certificate': True},
        'contracts/global/question_dependencies.json': {'case_id': case_dir.name, 'dependencies': {}, 'rules': {'downstream_read_only': True, 'use_formal_outputs_only': True}},
        'contracts/global/submission_contract.json': {'case_id': case_dir.name, 'required_submission_files': [], 'package_manifest_required': True, 'sha256_required': True},
        'contracts/global/agent_protocol_contract.json': {'case_id': case_dir.name, 'status': 'draft', 'required_for_final': {'parse_review': False, 'modeling_artifacts': False, 'verifier_plugins': False, 'paper_quality': False, 'figure_manifest': False}, 'notes': 'Set flags to true for strict official-contest dry runs.'},
    }
    for rel, data in global_defaults.items():
        p = case_dir / rel
        if not p.exists():
            write_json(p, data)
    return {'status': 'ok', 'case_dir': str(case_dir), 'created_dirs': dirs}

def registry_questions(case_dir: Path) -> list[dict]:
    reg = read_json(Path(case_dir) / 'registry' / 'questions_registry.json', {'questions': []}) or {'questions': []}
    return list(reg.get('questions', []))

def get_question(case_dir: Path, question_id: str) -> dict:
    for q in registry_questions(case_dir):
        if (q.get('question_id') or q.get('id')) == question_id:
            return q
    return {'question_id': question_id, 'title': question_id, 'required': True, 'type': 'unknown', 'status': 'new'}

def upsert_question(case_dir: Path, q: dict, preserve_existing: bool = True) -> dict:
    case_dir = Path(case_dir).resolve(); ensure_case_scaffold(case_dir)
    reg_path = case_dir / 'registry' / 'questions_registry.json'
    reg = read_json(reg_path, {'case_id': case_dir.name, 'questions': []}) or {'case_id': case_dir.name, 'questions': []}
    qid = q.get('question_id') or q.get('id')
    out = [] ; found = False
    for old in reg.get('questions', []):
        oid = old.get('question_id') or old.get('id')
        if oid == qid:
            merged = dict(old) if preserve_existing else {}
            merged.update({k:v for k,v in q.items() if v is not None})
            merged['question_id'] = qid
            out.append(merged); found = True
        else:
            out.append(old)
    if not found:
        nq = {'question_id': qid, 'title': q.get('title') or qid, 'type': q.get('type','unknown'), 'required': q.get('required', True), 'depends_on': q.get('depends_on', []), 'status': q.get('status','activated')}
        nq.update(q)
        out.append(nq)
    reg['questions'] = out; reg['question_count'] = len(out)
    write_json(reg_path, reg)
    return get_question(case_dir, qid)

def build_question_contract(case_dir: Path, question_id: str, qtype: str | None = None, title: str | None = None, force: bool = False) -> dict:
    case_dir = Path(case_dir).resolve(); ensure_case_scaffold(case_dir)
    os_root = _os_root_from_case(case_dir)
    q = get_question(case_dir, question_id)
    if qtype: q['type'] = qtype
    if title: q['title'] = title
    q['question_id'] = question_id
    q = upsert_question(case_dir, q)
    contract_dir = case_dir / 'contracts' / 'questions' / question_id
    contract_dir.mkdir(parents=True, exist_ok=True)
    repl = {'__QUESTION__': question_id, '__CASE_ID__': case_dir.name, '__TITLE__': q.get('title',question_id), '__TYPE__': q.get('type','unknown'), '__REQUIRED__': str(q.get('required', True)).lower()}
    tpl_dir = os_root / 'templates' / 'contracts_question'
    created = []
    for fname in QUESTION_CONTRACT_FILES:
        src = tpl_dir / fname
        dst = contract_dir / fname
        if src.exists() and (force or not dst.exists()):
            _copy_with_replacements(src, dst, repl)
            created.append(str(dst.relative_to(case_dir)))
    # enrich problem_spec with registry values and source excerpt
    ps = read_json(contract_dir / 'problem_spec.json', {}) or {}
    ps.update({'question_id': question_id, 'title': q.get('title', question_id), 'problem_type': q.get('type','unknown'), 'source_excerpt': q.get('source_excerpt',''), 'status': ps.get('status','draft')})
    if not ps.get('description') or ps.get('description') == '待填写':
        ps['description'] = q.get('source_excerpt','')[:1000] or '待填写'
    write_json(contract_dir / 'problem_spec.json', ps)
    return {'status': 'ok', 'question_id': question_id, 'contract_dir': str(contract_dir), 'created': created}

def activate_question(case_dir: Path, question_id: str, qtype: str = 'generic_optimization', title: str | None = None, required: bool | None = None, force: bool = False) -> dict:
    case_dir = Path(case_dir).resolve(); ensure_case_scaffold(case_dir)
    os_root = _os_root_from_case(case_dir)
    old = get_question(case_dir, question_id)
    resolved_type, type_resolution = _resolve_auto_question_type(case_dir, question_id, qtype, old)
    q = dict(old)
    q.update({'question_id': question_id, 'type': resolved_type or old.get('type','unknown'), 'title': title or old.get('title') or question_id, 'status': 'activated', 'type_resolution': type_resolution})
    if required is not None:
        q['required'] = required
    q = upsert_question(case_dir, q)
    contract_result = build_question_contract(case_dir, question_id, qtype=q.get('type'), title=q.get('title'), force=force)
    # Engineering scaffold
    src_candidates = [os_root / 'templates' / 'question_types' / q.get('type','') , os_root / 'templates' / 'question_engineering']
    src = next((s for s in src_candidates if (s / 'run.py').exists()), os_root / 'templates' / 'question_engineering')
    dst = case_dir / 'engineering' / 'questions' / question_id
    dst.mkdir(parents=True, exist_ok=True)
    copied = []
    for item in src.iterdir():
        if item.is_file() and item.suffix in {'.py','.md'}:
            target = dst / item.name
            if force or not target.exists():
                text = item.read_text(encoding='utf-8')
                text = text.replace('__QUESTION__', question_id).replace('__CASE_ID__', case_dir.name).replace('__TITLE__', q.get('title',question_id))
                target.write_text(text, encoding='utf-8')
                copied.append(str(target.relative_to(case_dir)))
    # Agent task cards
    cards = create_task_cards(case_dir, q, force=force)
    update_question_status(case_dir, question_id, 'activated', {'type': q.get('type'), 'title': q.get('title')})
    return {'status': 'ok', 'question': q, 'contracts': contract_result, 'engineering_files': copied, 'task_cards': cards}

def create_task_cards(case_dir: Path, q: dict, force: bool = False) -> list[str]:
    os_root = _os_root_from_case(case_dir)
    out_dir = Path(case_dir) / '.agent' / 'task_cards'
    out_dir.mkdir(parents=True, exist_ok=True)
    repl = {'__QUESTION__': q.get('question_id'), '__CASE_ID__': Path(case_dir).name, '__TITLE__': q.get('title',''), '__TYPE__': q.get('type','unknown'), '__REQUIRED__': str(q.get('required', True)).lower()}
    mapping = {
        'question_task_card.md': f"{q.get('question_id')}_task_card.md",
        'solver_task_card.md': f"{q.get('question_id')}_solver_task_card.md",
        'review_task_card.md': f"{q.get('question_id')}_review_task_card.md",
    }
    created=[]
    for src_name, dst_name in mapping.items():
        src = os_root / 'templates' / 'agent_cards' / src_name
        dst = out_dir / dst_name
        if src.exists() and (force or not dst.exists()):
            _copy_with_replacements(src, dst, repl)
            created.append(str(dst.relative_to(case_dir)))
    return created

def update_question_status(case_dir: Path, question_id: str, status: str, extra: dict | None = None) -> None:
    case_dir = Path(case_dir)
    path = case_dir / '.agent' / 'question_status' / 'case_status.json'
    data = read_json(path, {'case_id': case_dir.name, 'questions': {}}) or {'case_id': case_dir.name, 'questions': {}}
    data.setdefault('questions', {})[question_id] = {'status': status, 'updated_at': now_iso(), **(extra or {})}
    data['last_updated_at'] = now_iso()
    write_json(path, data)

def check_contracts(case_dir: Path, question_id: str | None = None) -> dict:
    case_dir = Path(case_dir).resolve()
    failures=[]; warnings=[]
    if not (case_dir / 'contracts' / 'global').exists():
        failures.append({'code': 'MISSING_GLOBAL_CONTRACTS', 'path': 'contracts/global'})
    questions = [get_question(case_dir, question_id)] if question_id else registry_questions(case_dir)
    if not questions:
        failures.append({'code': 'NO_QUESTIONS_IN_REGISTRY', 'message': 'No questions are registered; run problem-parse and question-activate first.'})
    for q in questions:
        qid = q.get('question_id') or q.get('id')
        qdir = case_dir / 'contracts' / 'questions' / qid
        if not qdir.exists():
            failures.append({'code': 'MISSING_QUESTION_CONTRACT_DIR', 'question_id': qid})
            continue
        for fname in QUESTION_CONTRACT_FILES[:13]:
            if not (qdir / fname).exists():
                failures.append({'code': 'MISSING_CONTRACT_FILE', 'question_id': qid, 'file': fname})
        failures.extend(_semantic_contract_failures(qdir, qid))
        if not (qdir / 'model_fidelity_contract.json').exists():
            warnings.append({'code': 'MISSING_MODEL_FIDELITY_CONTRACT', 'question_id': qid, 'message': 'v5.3 recommends model_fidelity_contract.json for optimism control'})
    report = {'gate': 'contract-check', 'question_id': question_id, 'status': 'failed' if failures else ('warning' if warnings else 'passed'), 'failures': failures, 'warnings': warnings}
    write_json(case_dir / '.agent' / 'gate_reports' / (f'{question_id}_contract_check.json' if question_id else 'case_contract_check.json'), report)
    return report


def _non_empty_list_or_dict(obj) -> bool:
    if isinstance(obj, list):
        return len(obj) > 0
    if isinstance(obj, dict):
        return any(v not in (None, '', [], {}) for v in obj.values())
    return bool(obj)


def _placeholderish_text(value) -> bool:
    text = str(value).lower()
    return bool(re.search(r'待填写|todo|placeholder|template|dummy|mock|agent 根据|激活后必须细化|generic|默认问题', text, re.I))


def _semantic_contract_failures(qdir: Path, qid: str) -> list[dict]:
    failures=[]
    ps = read_json(qdir / 'problem_spec.json', {}) or {}
    desc = str(ps.get('description') or ps.get('source_excerpt') or '').strip()
    if not desc or desc in {'待填写', 'TODO'} or _placeholderish_text(desc):
        failures.append({'code': 'EMPTY_OR_PLACEHOLDER_PROBLEM_SPEC_DESCRIPTION', 'question_id': qid, 'file': 'problem_spec.json'})
    variable = read_json(qdir / 'variable_registry.json', {}) or {}
    vars_ = variable.get('variables') or variable.get('decision_variables') or variable.get('inputs') or []
    if not _non_empty_list_or_dict(vars_) or _placeholderish_text(vars_):
        failures.append({'code': 'VARIABLE_REGISTRY_NOT_REFINED', 'question_id': qid, 'file': 'variable_registry.json'})
    else:
        names = {str(v.get('name','')).lower() for v in vars_ if isinstance(v, dict)}
        if names and names.issubset({'decision_variables','input_data'}):
            failures.append({'code': 'VARIABLE_REGISTRY_USES_DEFAULT_NAMES_ONLY', 'question_id': qid, 'file': 'variable_registry.json'})
    constraints = read_json(qdir / 'constraint_registry.json', {}) or {}
    cons = constraints.get('constraints') or constraints.get('hard_constraints') or []
    if not _non_empty_list_or_dict(cons) or _placeholderish_text(cons):
        failures.append({'code': 'CONSTRAINT_REGISTRY_NOT_REFINED', 'question_id': qid, 'file': 'constraint_registry.json'})
    validation = read_json(qdir / 'validation_contract.json', {}) or {}
    validators = validation.get('validators') or validation.get('checks') or validation.get('validation_items') or []
    if not _non_empty_list_or_dict(validators):
        failures.append({'code': 'VALIDATION_CONTRACT_EMPTY', 'question_id': qid, 'file': 'validation_contract.json'})
    else:
        string_validators = [str(x) for x in validators if isinstance(x, str)]
        has_structured_validator = any(isinstance(x, dict) and x.get('name') for x in validators)
        # Only a non-empty pure-string validator list equal to the generic template
        # should fail. A structured validator list with named checks is considered
        # refined and must not be rejected by the empty-set subset edge case.
        if string_validators and not has_structured_validator and set(string_validators).issubset({'schema_check','constraint_check','quality_claim_check'}):
            failures.append({'code': 'VALIDATION_CONTRACT_GENERIC_ONLY', 'question_id': qid, 'file': 'validation_contract.json'})
    output = read_json(qdir / 'output_contract.json', {}) or {}
    outputs = output.get('outputs') or output.get('required_outputs') or output.get('files') or []
    if not _non_empty_list_or_dict(outputs):
        failures.append({'code': 'OUTPUT_CONTRACT_EMPTY', 'question_id': qid, 'file': 'output_contract.json'})
    return failures
