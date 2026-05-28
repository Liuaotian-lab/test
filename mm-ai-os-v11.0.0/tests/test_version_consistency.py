from pathlib import Path
import json
import mmos
ROOT = Path(__file__).resolve().parents[1]
def test_version_consistency():
    version = (ROOT / 'VERSION.txt').read_text(encoding='utf-8').strip()
    assert mmos.__version__ == version
    assert json.loads((ROOT / 'os_manifest.json').read_text(encoding='utf-8'))['version'] == version
    assert json.loads((ROOT / 'contracts' / 'os_contract.json').read_text(encoding='utf-8'))['version'] == version
