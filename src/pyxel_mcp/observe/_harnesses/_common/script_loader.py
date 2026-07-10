"""Script import + cwd handling."""
from __future__ import annotations
import os
import sys
import types
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


def load_script_module(script_path: Path) -> types.ModuleType:
    """chdir to script's parent and execute the script as __main__.

    Returns the executed module object. The script may call `pyxel.init()` and
    `pyxel.run()` during execution; the caller is expected to have monkey-patched
    `pyxel.run` to intercept the loop.

    `__name__` is set to `"__main__"` so that `if __name__ == "__main__":` guards
    in user scripts are honoured — most real Pyxel scripts use this pattern.
    """
    parent = script_path.parent
    os.chdir(parent)
    if str(parent) not in sys.path:
        sys.path.insert(0, str(parent))

    source = script_path.read_text(encoding="utf-8")
    code = compile(source, str(script_path), "exec")

    mod = types.ModuleType("_user_script")
    mod.__file__ = str(script_path)
    mod.__name__ = "__main__"  # honour `if __name__ == "__main__":` guards
    mod.__spec__ = None
    sys.modules["_user_script"] = mod

    exec(code, mod.__dict__)
    return mod
