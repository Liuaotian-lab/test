#!/usr/bin/env python3
from __future__ import annotations
import os, shutil, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from mmos.contracts.manager import ensure_case_scaffold
from mmos.kernel.jsonio import write_json
from mmos.semantic_checks.temporal import temporal_semantics_check


def make_case(cid: str) -> Path:
    c=ROOT/'cases'/cid
    if c.exists(): shutil.rmtree(c)
    ensure_case_scaffold(c)
    write_json(c/'registry'/'questions_registry.json', {'case_id':cid,'questions':[{'question_id':'Q1','title':'问题1 单向阀每打开一次后关闭10ms，喷油器每秒工作10次','required':True,'status':'activated'}]})
    (c/'workspace').mkdir(exist_ok=True)
    (c/'workspace'/'problem_corpus.md').write_text('问题1 单向阀每打开一次后关闭10ms。喷油器每秒工作10次。', encoding='utf-8')
    return c


def test_temporal_semantics_catches_duty_cycle_equivalent():
    c=make_case('tmp_temporal_bad')
    out=c/'results'/'Q1'/'outputs'; out.mkdir(parents=True, exist_ok=True)
    write_json(out/'solution_real.json', {'question_id':'Q1','status':'success','metrics':{'stable_100_valve_open_ms':2.865,'stable_100_valve_period_ms':100.0},'diagnostics':{'temporal_semantics':{'valve_cycle_formula':'100ms injector duty cycle','valve_close_duration_ms':10.0,'valve_bound_to_injector_period':True}}})
    r=temporal_semantics_check(c, strict=True)
    assert r['status']=='failed', r
    assert any(f['code'] in {'VALVE_OPEN_DURATION_SEMANTICALLY_SUSPECT','VALVE_PERIOD_NOT_T_PLUS_10','VALVE_CYCLE_BOUND_TO_INJECTOR_PERIOD'} for f in r['failures'])


def test_temporal_semantics_accepts_t_plus_10():
    c=make_case('tmp_temporal_good')
    out=c/'results'/'Q1'/'outputs'; out.mkdir(parents=True, exist_ok=True)
    write_json(out/'solution_real.json', {'question_id':'Q1','status':'success','metrics':{'stable_100_valve_open_ms':0.288,'stable_100_valve_period_ms':10.288,'valve_close_duration_ms':10.0},'diagnostics':{'temporal_semantics':{'valve_cycle_formula':'T_open_ms + 10','valve_close_duration_ms':10.0,'stable_100_valve_period_ms':10.288,'injector_period_ms':100.0,'valve_bound_to_injector_period':False}}})
    r=temporal_semantics_check(c, strict=True)
    assert r['status']=='passed', r


if __name__ == '__main__':
    for fn in [test_temporal_semantics_catches_duty_cycle_equivalent, test_temporal_semantics_accepts_t_plus_10]:
        fn()
    print('fidelity-aware checks passed', flush=True); os._exit(0)
