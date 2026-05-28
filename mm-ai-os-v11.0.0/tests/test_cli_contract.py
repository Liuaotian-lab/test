from mmos.cli import build_parser


def _commands():
    parser = build_parser()
    for action in parser._actions:
        if getattr(action, 'choices', None):
            return set(action.choices.keys())
    return set()


def test_cli_help_mentions_v11():
    parser = build_parser()
    assert 'v11.0.0' in parser.description
    assert 'Dynamic Protocol Certified' in parser.description


def test_core_aliases_exist():
    cmds = _commands()
    for cmd in ['final-gate', 'package-submit', 'problem-understand', 'understanding-gate', 'search-plan-gate']:
        assert cmd in cmds


def test_legacy_commands_not_registered_in_pure_distribution():
    cmds = _commands()
    for cmd in ['capability-plan', 'capability-router', 'capability-atom', 'reference-free-plan', 'historical-benchmark-compare', 'benchmark-compare']:
        assert cmd not in cmds
