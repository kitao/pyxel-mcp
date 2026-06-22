"""Tests for the pyxel-mcp CLI (install / publish-skill subcommands).

The default `serve` subcommand starts the FastMCP server and is exercised
by the existing integration suite, so it's not re-tested here — the unit
tests here cover argparse wiring, install snippet output, and the
publish-skill copy semantics.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

import pytest

from pyxel_mcp import cli

ROOT = Path(__file__).resolve().parents[2]


def test_install_snippet_constant_is_valid_json():
    """The internal snippet constant parses cleanly as JSON."""
    parsed = json.loads(cli._INSTALL_SNIPPET)
    assert parsed["mcpServers"]["pyxel"]["command"] == "uvx"
    assert parsed["mcpServers"]["pyxel"]["args"] == ["pyxel-mcp"]


def test_registry_metadata_matches_project_version():
    """MCP registry metadata should not drift from the Python package."""
    pyproject = (ROOT / "pyproject.toml").read_text()
    project_version = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE).group(1)
    project_name = re.search(r'^name = "([^"]+)"$', pyproject, re.MULTILINE).group(1)
    registry = json.loads((ROOT / "server.json").read_text())

    assert registry["version"] == project_version
    assert len(registry["packages"]) == 1
    assert registry["packages"][0]["identifier"] == project_name
    assert registry["packages"][0]["version"] == project_version
    assert registry["packages"][0]["transport"]["type"] == "stdio"


def test_install_output_contains_snippet_text(capsys):
    """install output should embed the snippet so users can copy it directly."""
    rc = cli.main(["install"])
    assert rc == 0
    out = capsys.readouterr().out
    assert '"command": "uvx"' in out
    assert '"args": ["pyxel-mcp"]' in out
    assert '"mcpServers"' in out


def test_install_lists_known_host_config_paths(capsys):
    """The guide should at least mention Claude Code's config location."""
    cli.main(["install"])
    out = capsys.readouterr().out
    assert ".mcp.json" in out  # generic path users will recognise
    assert "claude" in out.lower()


def test_install_mentions_publish_skill_followup(capsys):
    """The install guide should point users to publish-skill for Layer 3."""
    cli.main(["install"])
    out = capsys.readouterr().out
    assert "publish-skill" in out


def test_publish_skill_copies_workflow_files(tmp_path):
    target = tmp_path / "skills" / "pyxel"
    rc = cli.main(["publish-skill", str(target)])
    assert rc == 0
    assert (target / "SKILL.md").is_file()
    assert (target / "knowledge" / "pixel-art.md").is_file()


def test_publish_skill_refuses_existing_target_without_force(tmp_path, capsys):
    target = tmp_path / "skills" / "pyxel"
    target.mkdir(parents=True)
    (target / "marker.txt").write_text("pre-existing\n")
    rc = cli.main(["publish-skill", str(target)])
    assert rc != 0
    err = capsys.readouterr().err
    assert "force" in err.lower() or "exists" in err.lower()
    # Existing content should be untouched.
    assert (target / "marker.txt").read_text() == "pre-existing\n"


def test_publish_skill_force_overwrites_existing_skill_dir(tmp_path):
    """--force on a directory that already looks like a skill dir
    (contains SKILL.md) is the supported overwrite path."""
    target = tmp_path / "skills" / "pyxel"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("# previous publish\n")
    (target / "stale.md").write_text("old\n")
    rc = cli.main(["publish-skill", str(target), "--force"])
    assert rc == 0
    assert not (target / "stale.md").exists()
    assert (target / "SKILL.md").is_file()
    assert (target / "SKILL.md").read_text() != "# previous publish\n"


def test_publish_skill_refuses_existing_non_skill_dir_even_with_force(tmp_path, capsys):
    """If the target is a non-empty dir without SKILL.md, --force still
    refuses — prevents wiping out an unrelated directory by typo."""
    target = tmp_path / "important"
    target.mkdir()
    (target / "important.txt").write_text("don't delete\n")
    rc = cli.main(["publish-skill", str(target), "--force"])
    assert rc != 0
    err = capsys.readouterr().err
    assert "non-skill" in err.lower() or "skill.md" in err.lower()
    assert (target / "important.txt").read_text() == "don't delete\n"


def test_publish_skill_force_overwrites_empty_existing_dir(tmp_path):
    """An empty existing dir is fine to overwrite with --force."""
    target = tmp_path / "skills" / "pyxel"
    target.mkdir(parents=True)
    rc = cli.main(["publish-skill", str(target), "--force"])
    assert rc == 0
    assert (target / "SKILL.md").is_file()


def test_publish_skill_refuses_file_target(tmp_path, capsys):
    target = tmp_path / "afile.txt"
    target.write_text("preserve me\n")
    rc = cli.main(["publish-skill", str(target)])
    assert rc != 0
    err = capsys.readouterr().err
    assert "file" in err.lower()
    assert target.read_text() == "preserve me\n"


def test_publish_skill_refuses_file_target_even_with_force(tmp_path, capsys):
    target = tmp_path / "afile.txt"
    target.write_text("preserve me\n")
    rc = cli.main(["publish-skill", str(target), "--force"])
    assert rc != 0
    assert target.read_text() == "preserve me\n"


def test_publish_skill_refuses_home_directory(tmp_path, monkeypatch, capsys):
    """`publish-skill ~ --force` must not nuke the user's home directory."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    (fake_home / "important.txt").write_text("don't delete\n")
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    rc = cli.main(["publish-skill", str(fake_home), "--force"])
    assert rc != 0
    err = capsys.readouterr().err
    assert "high-risk" in err.lower() or "refusing" in err.lower()
    assert (fake_home / "important.txt").exists()


def test_publish_skill_refuses_claude_config_root(tmp_path, monkeypatch, capsys):
    """`publish-skill ~/.claude --force` must not wipe out .mcp.json / CLAUDE.md."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    claude = fake_home / ".claude"
    claude.mkdir()
    (claude / ".mcp.json").write_text("{}\n")
    (claude / "CLAUDE.md").write_text("# my prefs\n")
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    rc = cli.main(["publish-skill", str(claude), "--force"])
    assert rc != 0
    err = capsys.readouterr().err
    assert "high-risk" in err.lower() or "refusing" in err.lower()
    assert (claude / ".mcp.json").read_text() == "{}\n"
    assert (claude / "CLAUDE.md").read_text() == "# my prefs\n"


def test_publish_skill_refuses_cursor_and_codex_config_roots(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    for name in (".cursor", ".codex", ".ssh", ".aws"):
        d = fake_home / name
        d.mkdir()
        rc = cli.main(["publish-skill", str(d), "--force"])
        assert rc != 0, f"should have refused {name}"


def test_publish_skill_refuses_filesystem_root(monkeypatch, capsys):
    """`publish-skill / --force` is refused at the dangerous-target gate."""
    rc = cli.main(["publish-skill", "/", "--force"])
    assert rc != 0
    err = capsys.readouterr().err
    assert "high-risk" in err.lower() or "refusing" in err.lower()


def test_publish_skill_friendly_error_when_workflow_missing(tmp_path, monkeypatch, capsys):
    """If workflow_root() raises, surface it as a normal error — not a traceback."""
    import pyxel_mcp.workflow as wf

    def boom():
        raise RuntimeError("simulated content loss")

    monkeypatch.setattr(wf, "workflow_root", boom)
    rc = cli.main(["publish-skill", str(tmp_path / "out")])
    assert rc != 0
    err = capsys.readouterr().err
    assert "simulated content loss" in err
    assert "Traceback" not in err


def test_publish_skill_dry_run_does_not_copy(tmp_path, capsys):
    target = tmp_path / "skills" / "pyxel"
    rc = cli.main(["publish-skill", str(target), "--dry-run"])
    assert rc == 0
    assert not target.exists()
    out = capsys.readouterr().out
    assert "dry" in out.lower() or "would" in out.lower()
    assert "SKILL.md" in out


def test_publish_skill_creates_parent_dirs(tmp_path):
    target = tmp_path / "deeply" / "nested" / "skills" / "pyxel"
    rc = cli.main(["publish-skill", str(target)])
    assert rc == 0
    assert (target / "SKILL.md").is_file()


def test_no_args_is_serve_default(monkeypatch):
    """`pyxel-mcp` with no subcommand should invoke server.main()."""
    called = {"yes": False}

    def fake_server_main():
        called["yes"] = True

    import pyxel_mcp.server
    monkeypatch.setattr(pyxel_mcp.server, "main", fake_server_main)
    cli.main([])
    assert called["yes"] is True


def test_serve_subcommand_invokes_server(monkeypatch):
    called = {"yes": False}

    def fake_server_main():
        called["yes"] = True

    import pyxel_mcp.server
    monkeypatch.setattr(pyxel_mcp.server, "main", fake_server_main)
    cli.main(["serve"])
    assert called["yes"] is True
