from pathlib import Path
from mmos.mcp_safety.policy import evaluate_mcp_safe_call


def test_mcp_candidate_write_allowed(tmp_path: Path):
    r=evaluate_mcp_safe_call(tmp_path, tool_class='candidate_write', target='workspace/x/candidate/out.json')
    assert r['allowed'] is True


def test_mcp_official_write_denied(tmp_path: Path):
    r=evaluate_mcp_safe_call(tmp_path, tool_class='candidate_write', target='workspace/x/official/out.json')
    assert r['allowed'] is False


def test_external_search_requires_provenance(tmp_path: Path):
    assert evaluate_mcp_safe_call(tmp_path, tool_class='external_search')['status']=='failed'
    assert evaluate_mcp_safe_call(tmp_path, tool_class='external_search', query='q', source_url='https://example.com')['status']=='passed'
