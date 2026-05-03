"""Tests for inspect_palette tool (spec §7.1)."""
from pyxel_mcp.observe._harnesses.tools.inspect_palette import run as inspect_palette_run
from tests.conftest import SCRIPTS


def test_default_palette_via_tool():
    result = inspect_palette_run({"script": str(SCRIPTS / "palette_default.py")})
    assert result["palette_size"] == 16
    assert result["errors"] == []


def test_extended_palette_via_tool():
    result = inspect_palette_run({"script": str(SCRIPTS / "palette_extended.py")})
    assert result["palette_size"] == 18
    assert result["hierarchy"] is None


def test_missing_script_validation_error():
    result = inspect_palette_run({"script": "/does/not/exist.py"})
    assert result["errors"][0]["phase"] == "validation"
