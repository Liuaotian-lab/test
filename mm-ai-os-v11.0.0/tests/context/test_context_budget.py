from pathlib import Path
from mmos.context.budget import context_build, context_check, context_compact

def test_context_build_check_compact(tmp_path: Path):
    assert context_build(tmp_path, 'solver_Q1')['status'] in {'passed','warning'}
    assert context_check(tmp_path)['status'] in {'passed','warning'}
    assert context_compact(tmp_path)['status'] in {'passed','warning'}
    assert (tmp_path/'state'/'case_state_summary.md').exists()
