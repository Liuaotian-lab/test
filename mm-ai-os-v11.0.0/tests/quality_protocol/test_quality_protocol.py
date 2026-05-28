from pathlib import Path
from mmos.kernel.jsonio import write_json
from mmos.quality_protocol.red_team import red_team_gate
from mmos.quality_protocol.review import quality_review


def test_red_team_blocks_false_optimality(tmp_path: Path):
    out=tmp_path/'results'/'Q1'/'outputs'; out.mkdir(parents=True)
    write_json(out/'solution_real.json', {'question_id':'Q1','quality_level':'heuristic_feasible','optimal':True,'scope':'real','data_source':'problem_statement_derived'})
    r=red_team_gate(tmp_path)
    assert r['status']=='failed'
    assert any(i['issue_type']=='false_optimality_claim' for i in r['issues'])


def test_quality_review_reports_failed_report(tmp_path: Path):
    write_json(tmp_path/'reports'/'bad_report.json', {'status':'failed'})
    assert quality_review(tmp_path)['issues']
