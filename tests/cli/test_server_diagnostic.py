from pyxel_mcp import server


def test_startup_diagnostic_reports_tool_count_only(capsys):
    server._log_startup()
    err = capsys.readouterr().err
    assert "[pyxel-mcp] starting - 9 tools" in err
    assert "9 tools" in err
    assert "workflow=" not in err
    assert "unavailable" not in err
