"""Tests for the pyxel-mcp CLI install and serve subcommands."""
from __future__ import annotations
import json
import re
import textwrap
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


def test_public_descriptions_preserve_observation_boundary():
    pyproject = (ROOT / "pyproject.toml").read_text()
    parser = cli._build_parser()

    assert "observe Pyxel programs" in pyproject
    assert "verify, and iterate" not in pyproject
    assert parser.description == "MCP server for Pyxel - headless observation tools."


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


def test_install_does_not_mention_skill_distribution(capsys):
    cli.main(["install"])
    out = capsys.readouterr().out.lower()
    assert "publish-skill" not in out
    assert "skill" not in out


def test_publish_skill_command_is_not_available(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["publish-skill", "somewhere"])
    assert excinfo.value.code != 0
    err = capsys.readouterr().err.lower()
    assert "invalid choice" in err


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


def test_readme_contains_cli_install_snippet_verbatim():
    """README and CLI must not drift; the CLI constant is the single source."""
    readme = (ROOT / "README.md").read_text()
    indented = textwrap.indent(cli._INSTALL_SNIPPET, "   ")
    assert indented in readme
