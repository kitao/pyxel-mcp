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


def test_startup_diagnostic_records_live_tool_count(capsys, monkeypatch):
    """The diagnostic should print a live tool count derived from the
    FastMCP registry, not a hard-coded number — so it stays accurate as
    the tool surface evolves."""
    import pyxel_mcp.server as srv
    monkeypatch.setattr(srv.mcp, "run", lambda: None)
    srv.main()
    err = capsys.readouterr().err
    # The string should mention "tools" and a non-zero count.
    import re
    m = re.search(r"(\d+) tools", err)
    assert m is not None, f"no tool count in stderr: {err!r}"
    assert int(m.group(1)) > 0


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
