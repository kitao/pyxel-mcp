"""Tests for _validate module."""

from pyxel_mcp._common.validate import validate_source


def test_valid_script():
    src = '''
import pyxel
class App:
    def __init__(self):
        pyxel.init(160, 120)
        pyxel.run(self.update, self.draw)
    def update(self):
        pass
    def draw(self):
        pyxel.cls(0)
App()
'''
    result = validate_source(src, "test.py")
    assert "No issues" in result


def test_syntax_error():
    result = validate_source("def foo(\n", "bad.py")
    assert "Syntax error" in result


def test_missing_import():
    result = validate_source("pyxel.init(160, 120)\npyxel.show()", "t.py")
    assert "import pyxel" in result


def test_missing_init():
    result = validate_source("import pyxel\npyxel.show()", "t.py")
    assert "pyxel.init()" in result


def test_missing_game_loop():
    result = validate_source("import pyxel\npyxel.init(160,120)", "t.py")
    assert "run()" in result or "show()" in result


def test_run_in_draw():
    src = '''
import pyxel
class App:
    def __init__(self):
        pyxel.init(160,120)
        pyxel.run(self.update, self.draw)
    def update(self): pass
    def draw(self):
        pyxel.cls(0)
        pyxel.run(self.update, self.draw)
'''
    result = validate_source(src, "t.py")
    assert "draw()" in result and "run()" in result


def test_math_sin_warning():
    src = "import pyxel\nimport math\npyxel.init(160,120)\nx=math.sin(1)\npyxel.show()"
    result = validate_source(src, "t.py")
    assert "degrees" in result


def test_no_cls_in_draw():
    src = '''
import pyxel
class App:
    def __init__(self):
        pyxel.init(160,120)
        pyxel.run(self.update, self.draw)
    def update(self): pass
    def draw(self):
        pyxel.rect(0,0,10,10,7)
'''
    result = validate_source(src, "t.py")
    assert "cls" in result


def test_list_mutation_warning():
    src = '''
import pyxel
pyxel.init(160,120)
enemies = []
for e in enemies:
    enemies.remove(e)
pyxel.show()
'''
    result = validate_source(src, "t.py")
    assert "remove" in result.lower() or "mutation" in result.lower() or "iterat" in result.lower()


def test_blt_without_colkey():
    src = '''
import pyxel
class App:
    def __init__(self):
        pyxel.init(160,120)
        pyxel.run(self.update, self.draw)
    def update(self): pass
    def draw(self):
        pyxel.cls(0)
        pyxel.blt(0, 0, 0, 0, 0, 8, 8)
'''
    result = validate_source(src, "t.py")
    assert "colkey" in result.lower() or "blt" in result.lower()


def test_blt_with_colkey_no_warning():
    src = '''
import pyxel
class App:
    def __init__(self):
        pyxel.init(160,120)
        pyxel.run(self.update, self.draw)
    def update(self): pass
    def draw(self):
        pyxel.cls(0)
        pyxel.blt(0, 0, 0, 0, 0, 8, 8, colkey=0)
'''
    result = validate_source(src, "t.py")
    assert "colkey" not in result.lower() or "No issues" in result


def test_run_outside_init():
    src = '''
import pyxel
class App:
    def __init__(self):
        pyxel.init(160,120)
    def start(self):
        pyxel.run(self.update, self.draw)
    def update(self): pass
    def draw(self):
        pyxel.cls(0)
'''
    result = validate_source(src, "t.py")
    assert "start" in result and "run" in result.lower()


def test_run_in_draw_no_duplicate():
    """pyxel.run() in draw() should produce exactly one warning."""
    source = '''
import pyxel
class App:
    def __init__(self):
        pyxel.init(64, 64)
    def update(self):
        pass
    def draw(self):
        pyxel.run(self.update, self.draw)
'''
    result = validate_source(source)
    # Count lines containing a pyxel.run() warning (should be exactly 1)
    run_warning_lines = [line for line in result.splitlines() if "pyxel.run()" in line and line.strip().startswith("-")]
    assert len(run_warning_lines) == 1


def test_run_in_init_no_warning():
    src = '''
import pyxel
class App:
    def __init__(self):
        pyxel.init(160,120)
        pyxel.run(self.update, self.draw)
    def update(self): pass
    def draw(self):
        pyxel.cls(0)
App()
'''
    result = validate_source(src, "t.py")
    # Should not warn about run() placement
    assert "start" not in result
