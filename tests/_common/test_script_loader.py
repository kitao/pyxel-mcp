from pathlib import Path

import pytest

from pyxel_mcp.observe._harnesses._common.script_loader import (
    load_script_module,
    resolve_script_path,
)
from tests.conftest import SCRIPTS


def test_resolve_absolute_path_passes_through():
    abs_path = SCRIPTS / "minimal.py"
    assert resolve_script_path(str(abs_path)) == abs_path.resolve()


def test_resolve_relative_path_uses_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake_script = tmp_path / "foo.py"
    fake_script.write_text("# fake")
    assert resolve_script_path("foo.py") == fake_script.resolve()


def test_resolve_nonexistent_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        resolve_script_path(str(tmp_path / "nope.py"))


@pytest.fixture
def neutered_pyxel(monkeypatch):
    """Let fixture scripts import without touching a real Pyxel window."""
    for name in ("run", "init", "cls"):
        monkeypatch.setattr(f"pyxel.{name}", lambda *a, **kw: None)


def test_load_script_chdirs_to_parent(monkeypatch, tmp_path, neutered_pyxel):
    monkeypatch.chdir(tmp_path)  # load_script_module changes cwd for good
    abs_path = SCRIPTS / "minimal.py"

    load_script_module(abs_path)

    assert Path.cwd() == abs_path.parent.resolve()


def test_load_script_presents_the_script_as_main(monkeypatch, tmp_path, neutered_pyxel):
    """Scripts see the argv, name, and path they would get under `python game.py`."""
    import sys

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["pytest"])
    abs_path = SCRIPTS / "minimal.py"

    module = load_script_module(abs_path)

    assert sys.argv == [str(abs_path)]
    assert module.__name__ == "__main__"
    assert module.__file__ == str(abs_path)
    assert str(abs_path.parent) in sys.path
