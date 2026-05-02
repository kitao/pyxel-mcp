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


def test_nested_class_in_draw_not_flagged():
    """`self.X = ...` inside a class nested within draw() refers to the inner class's
    self, not the outer App.self — must not trigger update_in_draw.
    """
    src = SCRIPTS / "draw_with_nested_class.py"
    src.write_text(
        "import pyxel\n"
        "class App:\n"
        "    def __init__(self):\n"
        "        pyxel.init(64,64)\n"
        "        pyxel.run(self.update, self.draw)\n"
        "    def update(self): pass\n"
        "    def draw(self):\n"
        "        pyxel.cls(0)\n"
        "        class Helper:\n"
        "            def setup(self):\n"
        "                self.val = 42\n"
    )
    try:
        result = validate_run({"script": str(src)})
        cats = [i["category"] for i in result["issues"]]
        assert "anti_pattern.update_in_draw" not in cats
    finally:
        src.unlink()


def test_non_utf8_script_returns_validation_error():
    """Non-UTF8 bytes in the script should surface as a validation-phase error
    (with path populated), not as a script_import-phase error from main.py's
    catch-all (which would lose the path field).
    """
    bad = SCRIPTS / "non_utf8.py"
    bad.write_bytes(b"\xff\xfe# bad bytes\n")
    try:
        result = validate_run({"script": str(bad)})
        assert result["ok"] is False
        errs = [e for e in result["errors"] if e["phase"] == "validation"]
        assert errs, f"expected a validation error, got {result['errors']}"
        assert errs[0]["path"] == str(bad)
    finally:
        bad.unlink()


# ---------------------------------------------------------------------------
# New detectors (Task 2.2)
# ---------------------------------------------------------------------------


def test_assets_in_update_detected():
    result = validate_run({"script": str(SCRIPTS / "anti_assets_in_update.py")})
    cats = [i["category"] for i in result["issues"]]
    assert "anti_pattern.assets_in_update" in cats


def test_assets_in_draw_detected():
    """pyxel.images[N].set inside draw() is also flagged."""
    src = SCRIPTS / "_assets_in_draw_tmp.py"
    src.write_text(
        "import pyxel\n"
        "class App:\n"
        "    def __init__(self):\n"
        "        pyxel.init(64,64)\n"
        "        pyxel.run(self.update, self.draw)\n"
        "    def update(self): pass\n"
        "    def draw(self):\n"
        "        pyxel.images[1].set(0, 0, ['0000'])\n"
        "        pyxel.cls(0)\n"
    )
    try:
        result = validate_run({"script": str(src)})
        cats = [i["category"] for i in result["issues"]]
        assert "anti_pattern.assets_in_update" in cats
    finally:
        src.unlink()


def test_iter_modify_detected():
    result = validate_run({"script": str(SCRIPTS / "anti_iter_modify.py")})
    cats = [i["category"] for i in result["issues"]]
    assert "anti_pattern.iter_modify" in cats


def test_iter_range_not_flagged():
    """Iterating over range() is safe -- no false positive for iter_modify."""
    src = SCRIPTS / "_iter_range_tmp.py"
    src.write_text(
        "import pyxel\n"
        "class App:\n"
        "    def __init__(self):\n"
        "        self.items = [1,2,3]\n"
        "        pyxel.init(64,64)\n"
        "        pyxel.run(self.update, self.draw)\n"
        "    def update(self):\n"
        "        for i in range(len(self.items)):\n"
        "            self.items.append(i)\n"
        "    def draw(self):\n"
        "        pyxel.cls(0)\n"
    )
    try:
        result = validate_run({"script": str(src)})
        cats = [i["category"] for i in result["issues"]]
        assert "anti_pattern.iter_modify" not in cats
    finally:
        src.unlink()


def test_btn_one_shot_detected():
    result = validate_run({"script": str(SCRIPTS / "anti_btn_one_shot.py")})
    cats = [i["category"] for i in result["issues"]]
    assert "anti_pattern.btn_one_shot" in cats


def test_btnp_not_flagged():
    """pyxel.btnp() is the correct API for one-shot actions -- must not be flagged."""
    src = SCRIPTS / "_btnp_tmp.py"
    src.write_text(
        "import pyxel\n"
        "class App:\n"
        "    def __init__(self):\n"
        "        pyxel.init(64,64)\n"
        "        pyxel.run(self.update, self.draw)\n"
        "    def update(self):\n"
        "        if pyxel.btnp(pyxel.KEY_SPACE):\n"
        "            pyxel.play(3, 0)\n"
        "    def draw(self):\n"
        "        pyxel.cls(0)\n"
    )
    try:
        result = validate_run({"script": str(src)})
        cats = [i["category"] for i in result["issues"]]
        assert "anti_pattern.btn_one_shot" not in cats
    finally:
        src.unlink()


def test_palette_animation_detected():
    result = validate_run({"script": str(SCRIPTS / "anti_palette_animation.py")})
    cats = [i["category"] for i in result["issues"]]
    assert "anti_pattern.palette_animation" in cats


def test_palette_outside_loop_not_flagged():
    """pyxel.colors[N] = X outside a loop (e.g., in __init__) is fine."""
    src = SCRIPTS / "_palette_init_tmp.py"
    src.write_text(
        "import pyxel\n"
        "class App:\n"
        "    def __init__(self):\n"
        "        pyxel.init(64,64)\n"
        "        pyxel.colors[1] = 0xFF0000\n"
        "        pyxel.run(self.update, self.draw)\n"
        "    def update(self): pass\n"
        "    def draw(self):\n"
        "        pyxel.cls(0)\n"
    )
    try:
        result = validate_run({"script": str(src)})
        cats = [i["category"] for i in result["issues"]]
        assert "anti_pattern.palette_animation" not in cats
    finally:
        src.unlink()


def test_cls_missing_detected():
    result = validate_run({"script": str(SCRIPTS / "anti_cls_missing.py")})
    cats = [i["category"] for i in result["issues"]]
    assert "anti_pattern.cls_missing" in cats


def test_cls_present_not_flagged():
    """A draw() that calls cls() before any pixel-emitting API is clean."""
    src = SCRIPTS / "_cls_present_tmp.py"
    src.write_text(
        "import pyxel\n"
        "class App:\n"
        "    def __init__(self):\n"
        "        pyxel.init(64,64)\n"
        "        pyxel.run(self.update, self.draw)\n"
        "    def update(self): pass\n"
        "    def draw(self):\n"
        "        pyxel.cls(0)\n"
        "        pyxel.pset(10, 10, 7)\n"
    )
    try:
        result = validate_run({"script": str(src)})
        cats = [i["category"] for i in result["issues"]]
        assert "anti_pattern.cls_missing" not in cats
    finally:
        src.unlink()


def test_degree_radian_mix_detected():
    result = validate_run({"script": str(SCRIPTS / "anti_degree_radian_mix.py")})
    cats = [i["category"] for i in result["issues"]]
    assert "anti_pattern.degree_radian_mix" in cats


def test_only_math_sin_not_flagged():
    """Using only math.sin (no pyxel.sin/cos) should not trigger degree_radian_mix."""
    src = SCRIPTS / "_math_only_tmp.py"
    src.write_text(
        "import pyxel, math\n"
        "class App:\n"
        "    def __init__(self):\n"
        "        pyxel.init(64,64)\n"
        "        pyxel.run(self.update, self.draw)\n"
        "    def update(self): pass\n"
        "    def draw(self):\n"
        "        pyxel.cls(0)\n"
        "        x = int(math.sin(0.5) * 10)\n"
        "        pyxel.pset(x, 10, 7)\n"
    )
    try:
        result = validate_run({"script": str(src)})
        cats = [i["category"] for i in result["issues"]]
        assert "anti_pattern.degree_radian_mix" not in cats
    finally:
        src.unlink()


def test_issues_sorted_with_severity_tiebreak():
    """When two issues share a line, error sorts before warning."""
    # Construct a script where syntax error and a warning land at the same line.
    # We cannot have both simultaneously (syntax error prevents AST analysis),
    # so instead verify the sort key with a synthetic issue list.
    from pyxel_mcp._harnesses.tools.validate import _make_issue, _SEVERITY_ORDER

    issues = [
        _make_issue("warning", 5, 0, "anti_pattern.missing_colkey", "warn"),
        _make_issue("error", 5, 0, "syntax", "err"),
        _make_issue("info", 5, 0, "anti_pattern.btn_one_shot", "info"),
    ]
    issues.sort(key=lambda i: (i["line"], _SEVERITY_ORDER.get(i["severity"], 99)))
    assert [i["severity"] for i in issues] == ["error", "warning", "info"]
