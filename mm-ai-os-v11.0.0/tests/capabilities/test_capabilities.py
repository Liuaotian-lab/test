from pathlib import Path
from mmos.capabilities.loader import capability_list, capability_show

def test_capability_protocols_exist():
    r=capability_list(Path.cwd())
    assert r['capability_count']==10
    assert capability_show(Path.cwd(), 'geometry')['status']=='passed'
    assert 'mandatory_validators' in capability_show(Path.cwd(), 'geometry')['capability']
