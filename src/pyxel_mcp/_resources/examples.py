"""Pyxel official examples exposed as MCP resources.

Each example file is enumerated at registration time so list_resources
returns the full set, not just a template.
"""

import os

from pyxel_mcp._resources._pyxel_env import pyxel_dir


def _examples_dir():
    pyxel_root = pyxel_dir()
    if not pyxel_root:
        return None
    candidate = os.path.join(pyxel_root, "examples")
    return candidate if os.path.isdir(candidate) else None


def _scan_examples():
    """Return sorted list of example basenames (without .py)."""
    d = _examples_dir()
    if not d:
        return []
    names = []
    for entry in sorted(os.listdir(d)):
        if entry.endswith(".py") and not entry.startswith("_"):
            names.append(entry[:-3])
    return names


def _load_example(name):
    d = _examples_dir()
    if not d:
        return f"Pyxel is not installed; example '{name}' is unavailable."
    path = os.path.join(d, f"{name}.py")
    if not os.path.isfile(path):
        return f"Example '{name}' not found."
    with open(path) as f:
        return f.read()


def _make_reader(name):
    # Factory binds `name` into a fresh closure scope per call —
    # avoids Python's late-binding loop variable trap without
    # adding a function parameter (FastMCP would treat one as a URI param).
    def _read() -> str:
        return _load_example(name)
    return _read


def register(mcp):
    for name in _scan_examples():
        mcp.resource(
            f"pyxel://examples/{name}",
            name=f"Pyxel Example: {name}",
            description=f"Official Pyxel example: {name}.py",
            mime_type="text/x-python",
        )(_make_reader(name))
