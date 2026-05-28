import json
from pathlib import Path

from mmos.cli.main import main

ROOT = Path(__file__).resolve().parents[3]
VALID = ROOT / "tests" / "fixtures" / "schemas" / "problem_understanding" / "valid_final_problem_signature.json"
INVALID = ROOT / "tests" / "fixtures" / "schemas" / "problem_understanding" / "invalid_final_problem_signature.json"


def test_schema_list_cli_outputs_core_schemas(capsys):
    rc = main(["schema-list"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "passed"
    assert "problem_understanding/final_problem_signature" in payload["schemas"]


def test_schema_validate_cli_returns_zero_for_valid_file(capsys):
    rc = main(["schema-validate", "--schema", "problem_understanding/final_problem_signature", "--file", str(VALID)])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "passed"


def test_schema_validate_cli_returns_nonzero_for_invalid_file(capsys):
    rc = main(["schema-validate", "--schema", "problem_understanding/final_problem_signature", "--file", str(INVALID)])
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "failed"
    assert payload["error_count"] >= 1
