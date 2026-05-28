from __future__ import annotations

from mmos.contracts.manager import ensure_case_scaffold
from mmos.core.artifacts import (
    evaluate_write_permission,
    migrate_legacy_artifacts,
    promote_artifact,
    read_official_json,
    write_candidate_json,
)
from mmos.kernel.jsonio import write_json, read_json


def test_candidate_official_layout_created_by_scaffold(tmp_path):
    case_dir = tmp_path / "case_layout"
    ensure_case_scaffold(case_dir)
    for rel in [
        "workspace/problem_understanding/candidate",
        "workspace/problem_understanding/official",
        "workspace/problem_understanding/reports",
        "workspace/academic_search/candidate",
        "workspace/academic_search/official",
        "workspace/method_plan/candidate",
        "paper/candidate",
        "paper/official",
        ".agent/allowed_files/agent_write_policy.json",
    ]:
        assert (case_dir / rel).exists(), rel


def test_agent_write_policy_denies_official_and_allows_candidate(tmp_path):
    case_dir = tmp_path / "case_policy"
    ensure_case_scaffold(case_dir)
    manifest = read_json(case_dir / ".agent" / "allowed_files" / "agent_write_policy.json")
    assert evaluate_write_permission("workspace/problem_understanding/candidate/x.json", manifest)["decision"] == "allowed"
    assert evaluate_write_permission("workspace/problem_understanding/official/x.json", manifest)["decision"] == "denied"
    assert evaluate_write_permission("final_outputs/answer.xlsx", manifest)["decision"] == "denied"


def test_promote_artifact_validates_schema_and_mirrors_legacy(tmp_path):
    case_dir = tmp_path / "case_promote"
    ensure_case_scaffold(case_dir)
    candidate = {
        "schema_version": "7.4.0",
        "status": "passed",
        "case_id": "case_promote",
        "questions": {
            "Q1": {
                "question_id": "Q1",
                "goal": {"claim": "predict temperature", "evidence_ids": ["EVID-Q1-0001"]},
                "source_evidence_ids": ["EVID-Q1-0001"],
            }
        },
    }
    write_candidate_json(case_dir, "workspace/problem_understanding/final_problem_signature.json", candidate, mirror_legacy=False)
    result = promote_artifact(
        case_dir,
        "workspace/problem_understanding/candidate/final_problem_signature.json",
        "workspace/problem_understanding/official/final_problem_signature.json",
        schema="problem_understanding/final_problem_signature",
        mirror_legacy="workspace/problem_understanding/final_problem_signature.json",
    )
    assert result.status == "passed"
    assert read_official_json(case_dir, "workspace/problem_understanding/final_problem_signature.json")["case_id"] == "case_promote"
    assert (case_dir / "workspace" / "problem_understanding" / "final_problem_signature.json").exists()


def test_migrate_legacy_artifacts_copies_to_official(tmp_path):
    case_dir = tmp_path / "case_migrate"
    ensure_case_scaffold(case_dir)
    legacy = {"schema_version": "7.4.0", "status": "passed", "case_id": "case_migrate", "questions": {}}
    write_json(case_dir / "workspace" / "problem_understanding" / "final_problem_signature.json", legacy)
    report = migrate_legacy_artifacts(case_dir, overwrite=True)
    assert report["status"] == "passed"
    assert (case_dir / "workspace" / "problem_understanding" / "official" / "final_problem_signature.json").exists()
