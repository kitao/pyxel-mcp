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


def test_install_snippet_constant_is_valid_json():
    """The internal snippet constant parses cleanly as JSON."""
    parsed = json.loads(cli._INSTALL_SNIPPET)
    assert parsed["mcpServers"]["pyxel"]["command"] == "uvx"
    assert parsed["mcpServers"]["pyxel"]["args"] == ["pyxel-mcp"]


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


def test_publish_skill_force_overwrites_existing(tmp_path):
    target = tmp_path / "skills" / "pyxel"
    target.mkdir(parents=True)
    (target / "stale.md").write_text("old\n")
    rc = cli.main(["publish-skill", str(target), "--force"])
    assert rc == 0
    assert not (target / "stale.md").exists()
    assert (target / "SKILL.md").is_file()


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
