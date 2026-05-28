from pathlib import Path

from mmos.core.schema import list_schemas, schema_path, validate_json_file

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests" / "fixtures" / "schemas"


def test_schema_registry_lists_core_v73_schemas():
    schemas = set(list_schemas(ROOT))
    expected = {
        "problem_understanding/final_problem_signature",
        "problem_understanding/evidence_index",
        "academic_research/search_results",
        "academic_research/identified_method",
        "method_plan/method_plan",
        "agents/task_card",
        "gates/gate_result",
        "workflow/step_result",
    }
    assert expected <= schemas
    assert schema_path("problem_understanding/final_problem_signature", ROOT).exists()


def test_valid_problem_signature_fixture_passes_schema():
    result = validate_json_file(
        FIXTURES / "problem_understanding" / "valid_final_problem_signature.json",
        "problem_understanding/final_problem_signature",
        root=ROOT,
    )
    assert result.status == "passed"
    assert result.error_count == 0


def test_invalid_problem_signature_fixture_fails_schema():
    result = validate_json_file(
        FIXTURES / "problem_understanding" / "invalid_final_problem_signature.json",
        "problem_understanding/final_problem_signature",
        root=ROOT,
    )
    assert result.status == "failed"
    assert result.error_count >= 1


def test_valid_academic_search_fixture_passes_schema():
    result = validate_json_file(
        FIXTURES / "academic_research" / "valid_search_results.json",
        "academic_research/search_results",
        root=ROOT,
    )
    assert result.status == "passed"


def test_invalid_academic_search_fixture_fails_schema():
    result = validate_json_file(
        FIXTURES / "academic_research" / "invalid_search_results.json",
        "academic_research/search_results",
        root=ROOT,
    )
    assert result.status == "failed"


def test_valid_method_plan_fixture_passes_schema():
    result = validate_json_file(
        FIXTURES / "method_plan" / "valid_method_plan.json",
        "method_plan/method_plan",
        root=ROOT,
    )
    assert result.status == "passed"


def test_valid_gate_result_fixture_passes_schema():
    result = validate_json_file(
        FIXTURES / "gates" / "valid_gate_result.json",
        "gates/gate_result",
        root=ROOT,
    )
    assert result.status == "passed"
