"""Installed Pyxel and Pyxel Cube examples exposed through resource templates."""

from pathlib import Path

from mcp.server.mcpserver.exceptions import ResourceError

from pyxel_mcp._resources._pyxel_env import pyxel_dir


def _examples_dir() -> Path | None:
    pyxel_root = pyxel_dir()
    if not pyxel_root:
        return None
    candidate = Path(pyxel_root) / "examples"
    return candidate.resolve() if candidate.is_dir() else None


def _load_example(name: str, *, subdir: str = "") -> str:
    d = _examples_dir()
    if not d:
        raise ResourceError("Pyxel examples are unavailable")
    if not name or Path(name).name != name:
        raise ResourceError(f"Example '{name}' not found")
    parent = (d / subdir).resolve()
    path = (parent / f"{name}.py").resolve()
    if not parent.is_relative_to(d) or path.parent != parent or not path.is_file():
        raise ResourceError(f"Example '{name}' not found")
    return path.read_text(encoding="utf-8")


def register(mcp):
    @mcp.resource(
        "pyxel://examples/{name}",
        name="Installed Pyxel Example",
        description="Python source for a named example bundled with the installed Pyxel package.",
        mime_type="text/x-python",
    )
    def example(name: str) -> str:
        return _load_example(name)

    @mcp.resource(
        "pyxel://examples/cube/{name}",
        name="Installed Pyxel Cube Example",
        description="Python source for a Pyxel Cube example bundled with the installed Pyxel package.",
        mime_type="text/x-python",
    )
    def cube_example(name: str) -> str:
        return _load_example(name, subdir="cube")
