from pathlib import Path

from mmos.contracts.manager import ensure_case_scaffold
from mmos.kernel.jsonio import write_json
from mmos.problem_understanding import understand_problem
from mmos.academic_research_engine.search_orchestrator import orchestrate_academic_search
from mmos.core.schema import validate_json_file

ROOT = Path(__file__).resolve().parents[3]


def test_generated_understanding_and_search_artifacts_validate(tmp_path):
    case_dir = tmp_path / "schema_generated_case"
    ensure_case_scaffold(case_dir)
    (case_dir / "workspace" / "problem_corpus.md").write_text(
        "问题1：建立炉温曲线模型，考虑温度、时间和传送带速度。要求峰值温度不超过250摄氏度，并确定最优传送带速度。附件一给出实验数据。",
        encoding="utf-8",
    )
    write_json(case_dir / "workspace" / "problem_graph.json", {
        "questions": [{
            "question_id": "Q1",
            "title": "炉温曲线优化",
            "source_excerpt": "建立炉温曲线模型，峰值温度不超过250摄氏度，确定最优传送带速度。",
        }]
    })
    understand_problem(case_dir, strict=False)
    orchestrate_academic_search(case_dir, strict=False)

    checks = [
        ("problem_understanding/final_problem_signature", case_dir / "workspace" / "problem_understanding" / "final_problem_signature.json"),
        ("problem_understanding/understanding_gate_report", case_dir / "quality" / "understanding_gate_report.json"),
        ("academic_research/search_results", case_dir / "workspace" / "academic_search" / "search_results.json"),
    ]
    for schema_name, path in checks:
        result = validate_json_file(path, schema_name, root=ROOT)
        assert result.status == "passed", result.to_dict()
