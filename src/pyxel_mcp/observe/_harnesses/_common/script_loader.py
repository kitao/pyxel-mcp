"""Script import and process context handling."""

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
    """Execute the script as `__main__` from its own directory and return it.

    The working directory, `sys.path`, and `sys.argv` become what `python
    <script>` would give the script, so relative assets, sibling imports, and
    argv access behave normally. The caller is expected to have patched
    `pyxel.run` so the game loop is intercepted rather than started.
    """
    parent = script_path.parent
    os.chdir(parent)
    if str(parent) not in sys.path:
        sys.path.insert(0, str(parent))
    sys.argv = [str(script_path)]

    mod = types.ModuleType("__main__")
    mod.__file__ = str(script_path)
    # compile(bytes) honors Python's source encoding cookie and UTF-8 BOM.
    source = script_path.read_bytes()
    code = compile(source, str(script_path), "exec")
    # Imports, dataclass annotation resolution, and pickle all look up a
    # class's module through sys.modules. Keep the script registered through
    # its update/draw callbacks, just as when Python executes a script.
    sys.modules["__main__"] = mod
    exec(code, mod.__dict__)  # noqa: S102 - trusted local script, by design
    return mod
