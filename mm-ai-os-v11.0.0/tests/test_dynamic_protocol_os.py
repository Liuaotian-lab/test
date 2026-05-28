from pathlib import Path

from mmos.kernel.jsonio import write_json
from mmos.protocol_synthesis.type_infer import problem_type_infer
from mmos.protocol_synthesis.atom_matcher import capability_atom_match
from mmos.protocol_synthesis.protocol_synthesizer import protocol_synthesize
from mmos.protocol_synthesis.protocol_linter import protocol_lint
from mmos.protocol_synthesis.protocol_redteam import protocol_redteam
from mmos.protocol_synthesis.protocol_compiler import protocol_compile
from mmos.protocol_synthesis.gate import dynamic_protocol_gate
from mmos.dynamic_tests.builder import dynamic_validator_build, validator_adequacy_check_v2, mutation_test_build
from mmos.validators.runner import validator_test
from mmos.fidelity.dynamic_fidelity import model_fidelity_plan_build, dynamic_model_fidelity_check, claim_limit_check
from mmos.dynamic_certificates.planner import certificate_plan_synthesize, certificate_build_from_plan, certificate_check_v2
from mmos.final_gate_v3.final_gate import final_gate_v3

ROOT = Path(__file__).resolve().parents[1]


def _case(tmp_path: Path) -> Path:
    c = tmp_path / "case_dynamic"
    write_json(c / "registry" / "questions_registry.json", {"questions": [{"question_id": "Q1", "required": True}]})
    text = """
    建立坐标系，计算距离、单位、光线反射、阴影遮挡、输出 result.xlsx，
    并在满足约束条件下进行优化，使目标尽量大。
    """
    (c / "workspace").mkdir(parents=True, exist_ok=True)
    (c / "workspace" / "problem_corpus.md").write_text(text, encoding="utf-8")
    return c


def _solution(case: Path) -> None:
    out = case / "results" / "Q1" / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    (out / "artifact.txt").write_text("ok", encoding="utf-8")
    write_json(out / "solution_real.json", {
        "question_id": "Q1",
        "scope": "real",
        "data_source": "problem_statement_derived",
        "experiment_id": "Q1_exp",
        "model": "dynamic_protocol_fixture",
        "method": "deterministic_fixture_solver",
        "quality_level": "evaluated_best",
        "fidelity_level": "L2",
        "solver_status": "completed",
        "optimal": False,
        "metrics": {"value": 1.0},
        "violation_count": 0,
        "diagnostics": {"constraints_checked": True, "domain_validators_run": ["dynamic_domain_validator"], "fallback_used": False},
        "artifacts": ["results/Q1/outputs/artifact.txt"],
        "limitations": "Dynamic protocol fixture; candidate-level result only."
    })


def test_dynamic_protocol_pipeline_and_final_gate_v3(tmp_path):
    case = _case(tmp_path)
    assert problem_type_infer(case)["status"] == "passed"
    assert capability_atom_match(ROOT, case)["status"] == "passed"
    assert protocol_synthesize(ROOT, case)["status"] == "passed"
    assert protocol_lint(case)["status"] == "passed"
    assert protocol_redteam(case)["status"] == "passed"
    assert protocol_compile(case)["status"] == "passed"
    assert dynamic_protocol_gate(case)["status"] == "passed"

    assert dynamic_validator_build(case, all_questions=True)["status"] == "passed"
    assert mutation_test_build(case, all_questions=True)["status"] == "passed"
    assert validator_test(case)["status"] == "passed"
    assert validator_adequacy_check_v2(case, all_questions=True)["status"] == "passed"

    _solution(case)
    assert model_fidelity_plan_build(case, all_questions=True)["status"] == "passed"
    assert dynamic_model_fidelity_check(case)["status"] == "passed"
    assert claim_limit_check(case, all_questions=True)["status"] == "passed"

    assert certificate_plan_synthesize(case, all_questions=True)["status"] == "passed"
    assert certificate_build_from_plan(case, all_questions=True)["status"] == "passed"
    assert certificate_check_v2(case, all_questions=True)["status"] == "passed"
    # The legacy stale-output gate treats contract files as freshness sources.
    # In the real workflow solver runs after contracts; the fixture touches the result here.
    (case / "results" / "Q1" / "outputs" / "solution_real.json").touch()

    gate = final_gate_v3(case, root=ROOT, strict=True)
    assert gate["status"] == "passed"
    assert gate["dynamic_protocol_gate"] == "passed"


def test_claim_limit_blocks_global_overclaim(tmp_path):
    case = _case(tmp_path)
    capability_atom_match(ROOT, case)
    protocol_synthesize(ROOT, case)
    protocol_lint(case)
    protocol_compile(case)
    _solution(case)
    sol = case / "results" / "Q1" / "outputs" / "solution_real.json"
    obj = __import__('json').loads(sol.read_text(encoding='utf-8'))
    obj["quality_level"] = "global_optimal"
    obj["optimal"] = True
    sol.write_text(__import__('json').dumps(obj, ensure_ascii=False), encoding='utf-8')
    report = claim_limit_check(case, all_questions=True)
    assert report["status"] == "failed"
    assert any(f["code"] == "GLOBAL_OR_OPTIMAL_CLAIM_NOT_ALLOWED_BY_PROTOCOL" for f in report["failures"])
