"""Test the startup diagnostic written to stderr by server.main()."""
from __future__ import annotations

import pytest


def test_startup_diagnostic_writes_to_stderr(capsys, monkeypatch):
    """server.main() must emit one line to stderr before mcp.run()."""
    import pyxel_mcp.server as srv
    # Don't actually start the server (it would block on stdio).
    monkeypatch.setattr(srv.mcp, "run", lambda: None)
    srv.main()
    captured = capsys.readouterr()
    assert "pyxel-mcp" in captured.err
    assert "starting" in captured.err
    assert "workflow=" in captured.err
    # And critically, nothing on stdout (would corrupt MCP stdio frames).
    assert captured.out == ""


def test_startup_diagnostic_mentions_tool_layers(capsys, monkeypatch):
    """The line should record the 17-tool / 2-layer surface for sanity-check."""
    import pyxel_mcp.server as srv
    monkeypatch.setattr(srv.mcp, "run", lambda: None)
    srv.main()
    err = capsys.readouterr().err
    assert "Layer 1" in err
    assert "Layer 2" in err
    assert "17 tools" in err


def test_startup_diagnostic_survives_missing_workflow(capsys, monkeypatch):
    """If workflow_root() raises, the server must still start (degraded mode)."""
    import pyxel_mcp.server as srv

    def boom():
        raise RuntimeError("simulated absence")

    import pyxel_mcp.workflow as wf
    monkeypatch.setattr(wf, "workflow_root", boom)
    monkeypatch.setattr(srv.mcp, "run", lambda: None)
    srv.main()
    err = capsys.readouterr().err
    assert "workflow=<unavailable" in err
    assert "simulated absence" in err
