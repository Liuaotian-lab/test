from __future__ import annotations
from pathlib import Path
import re
from typing import Any
from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from mmos.quality_oracle.common import registry_questions


def _case_text(case_dir: Path) -> str:
    parts=[]
    for p in [case_dir/'workspace'/'problem_corpus.md', case_dir/'workspace'/'problem_graph.json']:
        if p.exists():
            parts.append(p.read_text(encoding='utf-8', errors='ignore'))
    return '\n'.join(parts)


def _solution(case_dir: Path, qid: str) -> dict[str, Any]:
    return read_json(case_dir/'results'/qid/'outputs'/'solution_real.json', {}) or {}


def _extract_question_text(case_dir: Path, qid: str) -> str:
    graph = read_json(case_dir/'workspace'/'problem_graph.json', {}) or {}
    for q in graph.get('questions', []):
        if (q.get('question_id') or q.get('id')) == qid:
            return ' '.join(str(q.get(k,'')) for k in ['title','text','source_excerpt','raw_text'])
    reg = read_json(case_dir/'registry'/'questions_registry.json', {}) or {}
    for q in reg.get('questions', []):
        if (q.get('question_id') or q.get('id')) == qid:
            return ' '.join(str(q.get(k,'')) for k in ['title','source_excerpt','description'])
    return _case_text(case_dir)


def _infer_temporal_contract(case_dir: Path, qid: str) -> dict[str, Any]:
    txt = _extract_question_text(case_dir, qid) + '\n' + _case_text(case_dir)
    contract: dict[str, Any] = {
        'question_id': qid,
        'detected_constraints': [],
        'risk_flags': [],
        'control_periods': [],
        'external_periods': [],
        'unit_expectations': [],
    }
    if re.search(r'关闭\s*10\s*ms|10\s*ms\s*关闭|关闭10ms', txt):
        contract['detected_constraints'].append({
            'code': 'VALVE_CLOSE_AFTER_OPEN_10MS',
            'meaning': 'A valve action period is T_open + 10 ms, not the injector 100 ms period.',
            'expected_cycle_expression': 'T_open_ms + 10',
        })
        contract['control_periods'].append({'object': 'one_way_valve', 'period_expression': 'T_open_ms + 10', 'close_duration_ms': 10.0})
    if re.search(r'每秒\s*工作\s*10\s*次|每秒工作10次|10\s*次', txt):
        contract['detected_constraints'].append({
            'code': 'INJECTOR_10_HZ',
            'meaning': 'Injector external excitation period is 100 ms.',
            'period_ms': 100.0,
        })
        contract['external_periods'].append({'object': 'injector', 'period_ms': 100.0, 'frequency_hz': 10.0})
    if re.search(r'rad\s*/\s*ms|rad/ms|rad\s*s|角速度', txt, re.I):
        contract['unit_expectations'].append({'quantity': 'angular_velocity', 'preferred_unit': 'rad/s', 'aliases': ['rad/ms must be converted to rad/s']})
    if 'VALVE_CLOSE_AFTER_OPEN_10MS' in [c['code'] for c in contract['detected_constraints']] and 'INJECTOR_10_HZ' in [c['code'] for c in contract['detected_constraints']]:
        contract['risk_flags'].append({'code': 'DISTINCT_VALVE_AND_INJECTOR_CYCLES', 'message': 'Do not bind valve open/close cycle to injector period unless explicitly justified.'})
    return contract


def temporal_semantics_extract(case_dir: Path, question_id: str | None = None, write: bool = True) -> dict[str, Any]:
    case_dir=Path(case_dir).resolve()
    qs = registry_questions(case_dir)
    if question_id:
        qs=[q for q in qs if (q.get('question_id') or q.get('id')) == question_id]
    reports=[]
    for q in qs:
        qid = q.get('question_id') or q.get('id')
        contract=_infer_temporal_contract(case_dir, qid)
        reports.append(contract)
        if write:
            write_json(case_dir/'workspace'/'temporal_semantics'/f'{qid}.temporal_contract.json', contract)
    report={'command':'temporal-semantics-extract','status':'passed','contracts':reports,'generated_at':now_iso()}
    if write:
        write_json(case_dir/'quality'/'temporal_semantics_extract.json', report)
    return report


def _metrics(solution: dict[str, Any]) -> dict[str, Any]:
    m = dict(solution.get('metrics') or {})
    for k,v in (solution.get('results') or {}).items() if isinstance(solution.get('results'), dict) else []:
        m.setdefault(k,v)
    return m


def temporal_semantics_check(case_dir: Path, question_id: str | None = None, strict: bool = True, write: bool = True) -> dict[str, Any]:
    case_dir=Path(case_dir).resolve()
    extract=temporal_semantics_extract(case_dir, question_id=question_id, write=True)
    failures=[]; warnings=[]; checked=[]
    for contract in extract.get('contracts', []):
        qid=contract['question_id']
        sol=_solution(case_dir, qid)
        m=_metrics(sol)
        has_valve_close=any(c.get('code')=='VALVE_CLOSE_AFTER_OPEN_10MS' for c in contract.get('detected_constraints', []))
        has_injector=any(c.get('code')=='INJECTOR_10_HZ' for c in contract.get('detected_constraints', []))
        # Only questions that actually report a valve-open decision are required
        # to prove the T+10ms valve-cycle semantics. Later questions may inherit
        # the same case text but optimize cam speed or relief-valve policy instead.
        pre_m=_metrics(_solution(case_dir, qid))
        if has_valve_close and has_injector and (qid == 'Q1' or any(k in pre_m for k in ['stable_100_valve_open_ms','T100_ms','stable_100_open_ms'])):
            # Look for explicit evidence that solver used valve cycle T+10 ms.
            diag=sol.get('diagnostics') if isinstance(sol.get('diagnostics'), dict) else {}
            sem=diag.get('temporal_semantics') if isinstance(diag.get('temporal_semantics'), dict) else {}
            valve_period = sem.get('valve_cycle_formula') or m.get('valve_cycle_formula')
            close_ms = sem.get('valve_close_duration_ms') or m.get('valve_close_duration_ms')
            open_ms = m.get('stable_100_valve_open_ms') or m.get('T100_ms') or m.get('stable_100_open_ms')
            period_ms = m.get('stable_100_valve_period_ms') or sem.get('stable_100_valve_period_ms')
            bound_to_injector = bool(sem.get('valve_bound_to_injector_period'))
            if open_ms is not None:
                try:
                    op=float(open_ms)
                    # In this problem class, the reference/physics-derived value should be sub-ms.
                    # A value near 2.8-3.0 ms is usually a 100ms duty-cycle equivalent of a 0.288ms/(10+T) strategy.
                    if op > 1.5 and not sem.get('open_duration_is_duty_equivalent'):
                        failures.append({'code':'VALVE_OPEN_DURATION_SEMANTICALLY_SUSPECT','question_id':qid,'value_ms':op,'message':'Open duration is too large for a T+10ms valve cycle; likely an injector-period duty-cycle equivalent.'})
                    if period_ms is not None:
                        per=float(period_ms)
                        if abs(per - (op + 10.0)) > max(0.05, 0.01*(op+10.0)):
                            failures.append({'code':'VALVE_PERIOD_NOT_T_PLUS_10','question_id':qid,'open_ms':op,'period_ms':per,'expected_period_ms':op+10.0})
                except Exception:
                    warnings.append({'code':'VALVE_OPEN_DURATION_NOT_NUMERIC','question_id':qid,'value':open_ms})
            else:
                failures.append({'code':'MISSING_VALVE_OPEN_DURATION_METRIC','question_id':qid})
            if bound_to_injector:
                failures.append({'code':'VALVE_CYCLE_BOUND_TO_INJECTOR_PERIOD','question_id':qid})
            if not valve_period and strict:
                failures.append({'code':'MISSING_VALVE_CYCLE_FORMULA_EVIDENCE','question_id':qid,'expected':'T_open_ms + 10'})
            if close_ms is not None:
                try:
                    if abs(float(close_ms)-10.0) > 1e-6:
                        failures.append({'code':'VALVE_CLOSE_DURATION_NOT_10MS','question_id':qid,'value':close_ms})
                except Exception:
                    pass
        checked.append({'question_id':qid,'constraints':contract.get('detected_constraints', [])})
    status='failed' if failures else ('warning' if warnings else 'passed')
    report={'gate':'temporal-semantics-check','status':status,'strict':strict,'checked':checked,'failures':failures,'warnings':warnings,'generated_at':now_iso()}
    if write:
        write_json(case_dir/'quality'/'temporal_semantics_check.json', report)
        write_json(case_dir/'.agent'/'gate_reports'/'temporal_semantics_check.json', report)
    return report
