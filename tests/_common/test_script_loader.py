import os
import pytest
from pathlib import Path
from pyxel_mcp._harnesses._common.script_loader import resolve_script_path, load_script_module
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


def test_load_script_chdirs_to_parent(monkeypatch, tmp_path):
    """After load, cwd should be the script's parent."""
    monkeypatch.chdir(tmp_path)  # restore cwd after test (load_script_module does an unscoped os.chdir)
    abs_path = SCRIPTS / "minimal.py"
    monkeypatch.setattr("pyxel.run", lambda *a, **kw: None)  # neuter pyxel.run for import
    monkeypatch.setattr("pyxel.init", lambda *a, **kw: None)  # neuter pyxel.init
    monkeypatch.setattr("pyxel.cls", lambda *a, **kw: None)
    load_script_module(abs_path)
    assert Path.cwd() == abs_path.parent.resolve()
