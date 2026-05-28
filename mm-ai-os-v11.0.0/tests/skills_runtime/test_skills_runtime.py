from pathlib import Path
from mmos.skills_runtime.loader import list_skills, show_skill
from mmos.skills_runtime.runner import run_skill, check_skill
from mmos.modeling_os.common import write_json


def test_skill_list_and_show():
    root=Path.cwd()
    assert list_skills(root)['skill_count'] >= 1
    assert show_skill(root, 'problem_router')['status']=='passed'


def test_skill_run_writes_candidate_only(tmp_path: Path):
    r=run_skill(Path.cwd(), tmp_path, 'problem_router')
    assert r['status']=='passed'
    assert (tmp_path/'workspace'/'routing'/'candidate'/'problem_routing_proposal.json').exists()
    assert check_skill(Path.cwd(), tmp_path, 'problem_router')['status']=='passed'


def test_missing_manifest_fails(tmp_path: Path):
    assert run_skill(Path.cwd(), tmp_path, 'missing_skill')['status']=='failed'
