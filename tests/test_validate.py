"""Tests for _validate module."""

from pyxel_mcp._validate import validate_source


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
