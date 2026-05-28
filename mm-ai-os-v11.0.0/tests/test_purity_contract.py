from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_pure_distribution_has_no_historical_cases_or_legacy_modules():
    forbidden = [
        ROOT / 'legacy',
        ROOT / 'examples',
        ROOT / 'dev_tools' / 'historical_regression',
        ROOT / 'mmos' / 'capability_router',
        ROOT / 'mmos' / 'capability_planning',
        ROOT / 'tests' / 'legacy',
    ]
    for path in forbidden:
        assert not path.exists(), f'pure distribution must not include {path}'

def test_readme_does_not_reference_legacy_archives():
    text = (ROOT / 'README.md').read_text(encoding='utf-8')
    forbidden_terms = ['legacy_cases_archive', 'legacy/v6_capability_system', '历史案例归档']
    for term in forbidden_terms:
        assert term not in text
