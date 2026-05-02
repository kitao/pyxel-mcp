"""Script import + cwd handling (spec §5.2)."""
from __future__ import annotations
import importlib.util
import os
import sys
from pathlib import Path


def resolve_script_path(script: str) -> Path:
    """Resolve `script` to an absolute path; raise if not found."""
    p = Path(script)
    if not p.is_absolute():
        p = Path.cwd() / p
    p = p.resolve()
    if not p.is_file():
        raise FileNotFoundError(f"script not found: {p}")
    return p


def load_script_module(script_path: Path) -> object:
    """chdir to script's parent and import the script as a module.

    Returns the imported module object. The script may call `pyxel.init()` and
    `pyxel.run()` during import; the caller is expected to have monkey-patched
    `pyxel.run` to intercept the loop.
    """
    parent = script_path.parent
    os.chdir(parent)
    if str(parent) not in sys.path:
        sys.path.insert(0, str(parent))
    spec = importlib.util.spec_from_file_location("_user_script", script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot create import spec for {script_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_user_script"] = mod
    spec.loader.exec_module(mod)
    return mod
