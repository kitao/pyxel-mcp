"""Tests for read_palette tool (spec §7.1)."""
from pyxel_mcp.observe._harnesses.tools.read_palette import run as read_palette_run
from tests.conftest import SCRIPTS


def test_default_palette_via_tool():
    result = read_palette_run({"script": str(SCRIPTS / "palette_default.py")})
    assert result["palette_size"] == 16
    assert result["errors"] == []


def test_extended_palette_via_tool():
    result = read_palette_run({"script": str(SCRIPTS / "palette_extended.py")})
    assert result["palette_size"] == 18
    assert result["extended_palette"] is True


def test_missing_script_validation_error():
    result = read_palette_run({"script": "/does/not/exist.py"})
    assert result["errors"][0]["phase"] == "validation"
