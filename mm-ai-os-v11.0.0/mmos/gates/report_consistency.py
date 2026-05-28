from __future__ import annotations
from pathlib import Path
import math
import re
from mmos.kernel.jsonio import read_json, write_json

NUMBER_RE = re.compile(r'[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?')
IMPORTANT_NUMERIC_KEYS = {
    'objective_value', 'score', 'value', 'total_cost', 'total_profit', 'annual_output_mw',
    'unit_area_output_kw_m2', 'accuracy', 'rmse', 'mae', 'mape', 'mean', 'std', 'ci95_low', 'ci95_high'
}


def _is_important_key(key: str) -> bool:
    leaf = key.split('.')[-1]
    return leaf in IMPORTANT_NUMERIC_KEYS or key.startswith('metrics.') or key.startswith('result_metrics.')


def _close(a: float, b: float, abs_tol: float, rel_tol: float) -> bool:
    return math.isclose(a, b, abs_tol=abs_tol, rel_tol=rel_tol)


def _aliases_for_field(field: str) -> list[str]:
    leaf = re.sub(r'\[\d+\]', '', field.split('.')[-1]).lower()
    aliases = {field.lower(), leaf, leaf.replace('_', ' ')}
    if leaf == 'objective_value':
        aliases.update({'objective', 'objective value', '目标值', '目标函数'})
    if leaf == 'score':
        aliases.update({'score', '得分'})
    if leaf in {'rmse', 'mae', 'mape'}:
        aliases.add(leaf.upper())
    if field.startswith('metrics.'):
        aliases.add(field.replace('_', ' ').lower())
    return [a for a in aliases if a]


def _line_has_field_alias(line: str, field: str) -> bool:
    lower = line.lower()
    return any(alias in lower or alias in line for alias in _aliases_for_field(field))


def _numbers(line: str) -> list[float]:
    return [float(x) for x in NUMBER_RE.findall(line)]


def _line_matches_claim(line: str, field: str, value: float, abs_tol: float, rel_tol: float) -> bool:
    if not _line_has_field_alias(line, field):
        return False
    return any(_close(value, n, abs_tol, rel_tol) for n in _numbers(line))


def _qid_from_solution_path(path: Path) -> str | None:
    parts = list(path.parts)
    for i, part in enumerate(parts):
        if part == 'results' and i + 1 < len(parts):
            return parts[i + 1]
    return None


def _candidate_reports_for_qid(report_texts: list[tuple[Path, str]], qid: str | None) -> list[tuple[Path, str]]:
    if not qid or len(report_texts) <= 1:
        return report_texts
    qid_l = qid.lower()
    selected = [(p, t) for p, t in report_texts if qid_l in str(p).lower()]
    if selected:
        return selected
    selected = [(p, t) for p, t in report_texts if re.search(fr'\b{re.escape(qid)}\b', t, flags=re.I)]
    return selected or report_texts


def collect_solution_numbers(case_dir: Path) -> list[dict]:
    """Collect numeric conclusion claims that must be report-bound and contradiction-free."""
    nums=[]
    results_root = case_dir / 'results'
    files=sorted(results_root.glob('*/outputs/solution_real.json')) if results_root.exists() else []
    for p in files:
        data = read_json(p, default=None)
        if data is None:
            continue
        qid = _qid_from_solution_path(p)
        def walk(obj, key=''):
            if isinstance(obj, dict):
                for k,v in obj.items():
                    walk(v, f'{key}.{k}' if key else k)
            elif isinstance(obj, list):
                for i,v in enumerate(obj):
                    walk(v, f'{key}[{i}]')
            elif isinstance(obj, (int,float)) and not isinstance(obj, bool) and _is_important_key(key):
                nums.append({'path': str(p.relative_to(case_dir)), 'question_id': qid, 'field': key, 'value': float(obj)})
        walk(data)
    return nums


def report_consistency_check(case_dir: Path, report_path: str | None = None, abs_tol: float = 1e-4, rel_tol: float = 1e-3) -> dict:
    case_dir=Path(case_dir).resolve()
    if report_path:
        rp = Path(report_path)
        candidates=[case_dir/rp if not rp.is_absolute() else rp]
    else:
        candidates=list((case_dir/'reports').glob('*.md')) + list((case_dir/'final_outputs'/'submitted_files').rglob('*.md'))
    failures=[]; warnings=[]; checks=[]
    if not candidates:
        failures.append({'code': 'NO_REPORT_FOUND', 'message': 'No markdown report found under reports/ or final_outputs/submitted_files/.'})
    solution_nums=collect_solution_numbers(case_dir)
    if not solution_nums:
        warnings.append({'code': 'NO_NUMERIC_SOLUTION_CLAIMS_FOUND', 'message': 'No important numeric fields were found in solution outputs.'})
    report_texts=[]
    for rp in candidates:
        if not rp.exists():
            failures.append({'code':'REPORT_NOT_FOUND','path':str(rp)})
            continue
        text=rp.read_text(encoding='utf-8', errors='ignore')
        report_texts.append((rp, text))
        found=[float(x) for x in NUMBER_RE.findall(text)[:2000]]
        try:
            rel = str(rp.relative_to(case_dir))
        except ValueError:
            rel = str(rp)
        check={'report': rel, 'number_count': len(found), 'solution_number_count': len(solution_nums), 'matched_solution_numbers': []}
        if len(text) < 80:
            failures.append({'code':'REPORT_TOO_SHORT','path':rel,'min_chars':80})
        if 'generated by the generic question template' in text.lower() or 'replace with question-specific' in text.lower():
            failures.append({'code':'GENERIC_TEMPLATE_REPORT_NOT_ALLOWED','path':rel})
        if 'global_optimal' in text or '全局最优' in text:
            has_global=False
            for p in sorted((case_dir/'results').rglob('*.json')) if (case_dir/'results').exists() else []:
                d=read_json(p, default={}) or {}
                if d.get('quality_level') == 'global_optimal':
                    has_global=True
            if not has_global:
                failures.append({'code':'UNSUPPORTED_GLOBAL_OPTIMAL_LANGUAGE','path':rel})
        checks.append(check)
    unmatched=[]; conflicts=[]
    for sn in solution_nums:
        val=float(sn['value'])
        q_reports = _candidate_reports_for_qid(report_texts, sn.get('question_id'))
        matched=False
        field_lines=[]
        for rp, text in q_reports:
            for lineno, line in enumerate(text.splitlines(), start=1):
                if not _line_has_field_alias(line, sn['field']):
                    continue
                nums = _numbers(line)
                if not nums:
                    continue
                line_match = any(_close(val, n, abs_tol, rel_tol) for n in nums)
                if line_match:
                    matched=True
                else:
                    try:
                        rel = str(rp.relative_to(case_dir))
                    except ValueError:
                        rel = str(rp)
                    field_lines.append({'report': rel, 'line': lineno, 'field': sn['field'], 'expected_value': val, 'reported_numbers': nums[:10], 'text': line[:300]})
        if matched:
            for c in checks:
                c.setdefault('matched_solution_numbers', []).append({'question_id': sn.get('question_id'), 'field': sn['field'], 'value': val})
        else:
            unmatched.append(sn)
        conflicts.extend(field_lines)
    if unmatched:
        failures.append({'code':'SOLUTION_NUMBER_NOT_REPORTED', 'message':'Important numeric result values are absent from the report within tolerance.', 'unmatched':unmatched[:50]})
    if conflicts:
        failures.append({'code':'FIELD_NUMERIC_CONFLICT', 'message':'The report contains field-specific numeric claims that conflict with solution_real.json.', 'conflicts':conflicts[:50]})
    status='failed' if failures else ('warning' if warnings else 'passed')
    report={'gate':'report-consistency-check','status':status,'checks':checks,'failures':failures,'warnings':warnings,'abs_tol':abs_tol,'rel_tol':rel_tol}
    write_json(case_dir/'.agent'/'gate_reports'/'report_consistency_check.json', report)
    return report
