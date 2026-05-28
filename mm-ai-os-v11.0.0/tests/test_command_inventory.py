from pathlib import Path

from mmos.cli import build_parser

ROOT = Path(__file__).resolve().parents[1]


def _commands():
    parser = build_parser()
    for action in parser._actions:
        if getattr(action, "choices", None):
            return set(action.choices.keys())
    return set()


def test_command_inventory_covers_registered_commands():
    inventory = (ROOT / "docs" / "refactor" / "COMMAND_INVENTORY.md").read_text(encoding="utf-8")
    missing = [cmd for cmd in _commands() if f"`{cmd}`" not in inventory]
    assert not missing
