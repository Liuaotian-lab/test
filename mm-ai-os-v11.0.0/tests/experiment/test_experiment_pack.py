from pathlib import Path
from mmos.kernel.jsonio import write_json
from mmos.experiment.record import experiment_record
from mmos.experiment.pack import experiment_pack


def _solution(case: Path):
    out=case/'results'/'Q1'/'outputs'; out.mkdir(parents=True)
    (out/'result.xlsx').write_text('fixture', encoding='utf-8')
    write_json(out/'solution_real.json', {'question_id':'Q1','scope':'real','data_source':'problem_statement_derived','experiment_id':'Q1_exp','model':'m','method':'simulation','quality_level':'simulation_estimate','solver_status':'completed','optimal':False,'metrics':{'x':1},'violation_count':0,'diagnostics':{'constraints_checked':True,'domain_validators_run':['domain_validate','solver_verify'],'fallback_used':False},'artifacts':['results/Q1/outputs/result.xlsx'],'limitations':'No optimization claim.'})


def test_experiment_record_and_pack(tmp_path: Path):
    _solution(tmp_path)
    r=experiment_record(tmp_path, 'Q1')
    assert r['status']=='passed'
    p=experiment_pack(tmp_path)
    assert p['status']=='passed'
    assert (tmp_path/'reports'/'experiments_summary.jsonl').exists()


def test_experiment_missing_limitations_fails(tmp_path: Path):
    _solution(tmp_path)
    sol=tmp_path/'results'/'Q1'/'outputs'/'solution_real.json'
    import json
    data=json.loads(sol.read_text())
    data['limitations']=''
    write_json(sol, data)
    assert experiment_record(tmp_path, 'Q1')['status']=='failed'
