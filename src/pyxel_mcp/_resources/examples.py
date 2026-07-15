"""Installed Pyxel examples exposed through one resource template."""

from pathlib import Path

from pyxel_mcp._resources._pyxel_env import pyxel_dir


def _examples_dir() -> Path | None:
    pyxel_root = pyxel_dir()
    if not pyxel_root:
        return None
    candidate = Path(pyxel_root) / "examples"
    return candidate.resolve() if candidate.is_dir() else None


def _load_example(name: str) -> str:
    d = _examples_dir()
    if not d:
        raise ValueError("Pyxel examples are unavailable")
    if not name or Path(name).name != name:
        raise ValueError(f"Example '{name}' not found")
    path = (d / f"{name}.py").resolve()
    if path.parent != d or not path.is_file():
        raise ValueError(f"Example '{name}' not found")
    return path.read_text()


def register(mcp):
    @mcp.resource(
        "pyxel://examples/{name}",
        name="Installed Pyxel Example",
        description="Python source for a named example bundled with the installed Pyxel package.",
        mime_type="text/x-python",
    )
    def example(name: str) -> str:
        return _load_example(name)
