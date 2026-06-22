from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pyxel_mcp_does_not_ship_a_skill_tree():
    assert not (ROOT / "skill").exists()
    assert not (ROOT / "src" / "pyxel_mcp" / "workflow").exists()


def test_pyxel_mcp_public_docs_do_not_advertise_skill_distribution():
    public_files = [
        ROOT / "README.md",
        ROOT / "src" / "pyxel_mcp" / "instructions.md",
        ROOT / "src" / "pyxel_mcp" / "observe" / "_harnesses" / "tools" / "pyxel_info.py",
    ]
    offenders = []
    forbidden = ("publish-skill", "pyxel://workflow", "workflow skill", "SKILL.md")
    for path in public_files:
        text = path.read_text()
        for term in forbidden:
            if term in text:
                offenders.append(f"{path.relative_to(ROOT)}: {term}")
    assert offenders == []


def test_pyxel_mcp_has_no_skill_build_or_publish_plumbing():
    assert not (ROOT / "build_hooks.py").exists()
    pyproject = (ROOT / "pyproject.toml").read_text()
    forbidden = [
        "force-include",
        "tool.hatch.build.hooks.custom",
        "build_hooks.py",
        "workflow/_content",
    ]
    offenders = [term for term in forbidden if term in pyproject]
    assert offenders == []


def test_pyxel_mcp_source_does_not_import_workflow_package():
    offenders = []
    for path in (ROOT / "src").rglob("*.py"):
        text = path.read_text()
        if "pyxel_mcp.workflow" in text or "workflow_root" in text:
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_pyxel_mcp_cli_has_only_mcp_commands():
    from pyxel_mcp import cli

    parser = cli._build_parser()
    subparsers = [
        action for action in parser._actions
        if getattr(action, "choices", None)
    ]
    choices = set(subparsers[0].choices)
    assert choices == {"serve", "install"}
