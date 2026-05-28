import pytest
from mmos.kernel.paths import OSPaths
def test_case_id_rejects_path_traversal():
    osp = OSPaths.discover()
    for bad in ['../evil', '../../tmp/x', 'case/evil', 'case..evil']:
        with pytest.raises(ValueError): osp.case_dir(bad)
