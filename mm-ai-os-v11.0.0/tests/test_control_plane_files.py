from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_schema_gated_files_exist():
    required = [
        "AGENTS.md",
        "VERSION_CODENAME",
        "context_packs/global.md",
        "context_packs/cli.md",
        "context_packs/understanding.md",
        "context_packs/research.md",
        "context_packs/contracts.md",
        "context_packs/gates.md",
        "context_packs/paper.md",
        "docs/refactor/CURRENT_ARCHITECTURE.md",
        "docs/refactor/MODULE_INVENTORY.md",
        "docs/refactor/COMMAND_INVENTORY.md",
        "docs/refactor/ARTIFACT_INVENTORY.md",
        "docs/refactor/RISK_REGISTER.md",
    ]
    for rel in required:
        assert (ROOT / rel).exists(), rel


def test_context_pack_size_budget():
    for path in (ROOT / "context_packs").glob("*.md"):
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        assert line_count <= 300, f"{path.name} exceeds context-pack budget: {line_count} lines"
