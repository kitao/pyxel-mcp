from pathlib import Path


def test_instructions_present():
    # Resolve relative to this file so the test works regardless of CWD.
    repo_root = Path(__file__).parent.parent.parent
    text = (repo_root / "src/pyxel_mcp/instructions.md").read_text()
    for marker in ["## Tools at a glance", "## Workflow patterns", "## Quirks", "pyxel://run-snapshots-schema"]:
        assert marker in text, f"missing section: {marker}"
