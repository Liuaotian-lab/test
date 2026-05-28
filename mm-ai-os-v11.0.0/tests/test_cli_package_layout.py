from pathlib import Path

from mmos.cli import build_parser, main


ROOT = Path(__file__).resolve().parents[1]


def test_cli_package_layout_exists():
    assert (ROOT / "mmos" / "cli" / "main.py").exists()
    assert (ROOT / "mmos" / "cli" / "parser.py").exists()
    assert not (ROOT / "mmos" / "cli.py").exists()


def test_cli_exports_are_callable():
    assert callable(build_parser)
    assert callable(main)


def test_python_module_help_entrypoint():
    parser = build_parser()
    assert "Dynamic Protocol Certified" in parser.description
