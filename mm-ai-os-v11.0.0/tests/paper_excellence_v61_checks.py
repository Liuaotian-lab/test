from __future__ import annotations
import json, os, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mmos.contracts.manager import ensure_case_scaffold
from mmos.ingestion.document_ingestor import build_problem_corpus
from mmos.problem_graph.parser import build_problem_graph
from mmos.semantic_audit.auditor import semantic_audit
from mmos.paper_excellence.evidence_engine import (
    paper_evidence_graph, appendix_code_build, appendix_code_check, paper_readiness_gate,
    paper_argument_plan, figure_table_plan, paper_redteam_review
)
from mmos.paper_excellence.checks import paper_argument_check, paper_evidence_check
from mmos.paper_latex.latex import build_latex_source

def setup_case(case_id='paper_v61_case'):
    case_dir = ROOT / 'cases' / case_id
    if case_dir.exists(): shutil.rmtree(case_dir)
    ensure_case_scaffold(case_dir)
    raw = case_dir / 'data' / 'raw'; raw.mkdir(parents=True, exist_ok=True)
    (raw / 'problem.txt').write_text('2026 测试题\n问题1. 建立模型并给出最优参数和结果图。', encoding='utf-8')
    build_problem_corpus(case_dir)
    build_problem_graph(case_dir)
    semantic_audit(case_dir, strict=True)
    qdir = case_dir / 'results' / 'Q1' / 'outputs'; qdir.mkdir(parents=True, exist_ok=True)
    (qdir / 'solution_real.json').write_text(json.dumps({'question_id':'Q1','status':'passed','stage':'real','quality_level':'competition_candidate','metrics':{'optimal_parameter': 12.34, 'objective_value': 56.78}}, ensure_ascii=False), encoding='utf-8')
    fdir = case_dir / 'final_outputs'; fdir.mkdir(exist_ok=True)
    (fdir / 'result.csv').write_text('x,y\n1,2\n', encoding='utf-8')
    eng = case_dir / 'engineering' / 'questions' / 'Q1'; eng.mkdir(parents=True, exist_ok=True)
    (eng / 'solve.py').write_text('''import json\n\ndef solve():\n    result={"optimal_parameter":12.34,"objective_value":56.78}\n    return result\n\nif __name__ == "__main__":\n    print(json.dumps(solve(), ensure_ascii=False))\n''', encoding='utf-8')
    figs = case_dir / 'paper' / 'figures'; figs.mkdir(parents=True, exist_ok=True)
    (figs / 'q1_result.png').write_bytes(b'placeholder')
    (case_dir / 'paper' / 'figures_manifest.json').write_text(json.dumps({'figures':[{'figure_id':'q1_result','path':'paper/figures/q1_result.png','source_script':'engineering/questions/Q1/solve.py','paper_section':'五、模型的建立与求解','argument_supported':'展示 Q1 输出结果'}]}, ensure_ascii=False, indent=2), encoding='utf-8')
    return case_dir

def main():
    case_dir = setup_case()
    assert paper_evidence_graph(case_dir)['status'] == 'passed'
    assert appendix_code_build(case_dir, all_questions=True)['status'] == 'passed'
    assert appendix_code_check(case_dir, strict=True)['status'] == 'passed'
    ready = paper_readiness_gate(case_dir, target='national_first')
    assert ready['paper_generation_allowed'] is True, ready
    assert ready['paper_section_policy']['semantic_audit_as_section'] is False
    assert ready['paper_section_policy']['validation_as_large_section'] is True
    plan = paper_argument_plan(case_dir, target='national_first')
    assert '数据处理与语义审计' in plan['forbidden_front_stage_sections']
    assert any(s['section'] == '六、模型的分析与检验' for s in plan['front_stage_sections'])
    assert figure_table_plan(case_dir)['status'] in {'passed','warning'}
    build = build_latex_source(case_dir, force=True, template='cumcm_gold')
    assert build['status'] == 'passed'
    tex = (case_dir / 'paper_latex' / 'main_paper.tex').read_text(encoding='utf-8')
    assert '数据处理与语义审计' not in tex
    assert '附录 A' in tex and '完整程序代码' in tex
    assert '模型的分析与检验' in tex and '模型的评价与推广' in tex
    assert '\\tableofcontents' not in tex
    assert paper_argument_check(case_dir, strict=True)['status'] == 'passed'
    assert paper_evidence_check(case_dir, strict=True)['status'] == 'passed'
    red = paper_redteam_review(case_dir)
    assert 'paper_award_ceiling' in red
    print('paper_excellence_v61_checks passed', flush=True); os._exit(0)

if __name__ == '__main__':
    main()
