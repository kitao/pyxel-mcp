from pyxel_mcp._harnesses.tools.validate import run as validate_run
from tests.conftest import SCRIPTS


def test_minimal_script_is_ok():
    result = validate_run({"script": str(SCRIPTS / "minimal.py")})
    assert result["ok"] is True
    assert result["issues"] == []


def test_syntax_error_reported():
    """A script with bad syntax should produce a 'syntax' category error."""
    bad = SCRIPTS / "syntax_error.py"
    bad.write_text("def foo(:\n    pass\n")
    try:
        result = validate_run({"script": str(bad)})
        assert result["ok"] is False
        assert any(i["category"] == "syntax" for i in result["issues"])
    finally:
        bad.unlink()


def test_missing_colkey_detected():
    result = validate_run({"script": str(SCRIPTS / "anti_missing_colkey.py")})
    cats = [i["category"] for i in result["issues"]]
    assert "anti_pattern.missing_colkey" in cats


def test_update_in_draw_detected():
    result = validate_run({"script": str(SCRIPTS / "anti_update_in_draw.py")})
    cats = [i["category"] for i in result["issues"]]
    assert "anti_pattern.update_in_draw" in cats


def test_tilemap_zero_zero_detected():
    result = validate_run({"script": str(SCRIPTS / "anti_tilemap_zero_zero.py")})
    cats = [i["category"] for i in result["issues"]]
    assert "anti_pattern.tilemap_zero_zero" in cats


def test_issues_sorted_by_line_then_severity():
    """Per spec §8.1, issues sorted by line ascending, then severity error > warning > info."""
    src = SCRIPTS / "mixed_issues.py"
    src.write_text(
        "import pyxel\n"
        "class App:\n"
        "    def __init__(self):\n"
        "        pyxel.init(64,64)\n"
        "        pyxel.run(self.update, self.draw)\n"
        "    def update(self): pass\n"
        "    def draw(self):\n"
        "        pyxel.cls(0)\n"
        "        pyxel.blt(0,0,0,0,0,8,8)\n"
        "        pyxel.blt(0,0,0,0,0,8,8)\n"
    )
    try:
        result = validate_run({"script": str(src)})
        lines = [i["line"] for i in result["issues"]]
        assert lines == sorted(lines)
    finally:
        src.unlink()


def test_missing_script_returns_validation_error():
    result = validate_run({"script": "/nonexistent/path.py"})
    assert any(e["phase"] == "validation" for e in result["errors"])
