"""pyxel_info() — discovery (spec §8.2)."""
from __future__ import annotations
import sys
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any


def _stubs_path() -> str:
    import pyxel
    pyi = Path(pyxel.__file__).parent / "pyxel.pyi"
    return str(pyi) if pyi.is_file() else ""


def _examples() -> list[dict[str, Any]]:
    """Locate Pyxel example scripts shipped with the package."""
    import pyxel
    examples_dir = Path(pyxel.__file__).parent / "examples"
    if not examples_dir.is_dir():
        return []
    out = []
    for path in sorted(examples_dir.glob("*.py")):
        out.append({"name": path.stem, "path": str(path), "description": None})
    return out


def run(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "pyxel_mcp_version": _pkg_version("pyxel-mcp"),
        "pyxel_version": _pkg_version("pyxel"),
        "python_version": sys.version.split()[0],
        "stubs_path": _stubs_path(),
        "examples": _examples(),
        "resources": {
            "api_reference": "pyxel://api-reference",
            "user_guide": "pyxel://user-guide",
            "mml_commands": "pyxel://mml-commands",
            "pyxres_format": "pyxel://pyxres-format",
            "default_palette": "pyxel://palette/default",
            "examples": "pyxel://examples/<name>",
            "run_snapshots_schema": "pyxel://run-snapshots-schema",
        },
        "errors": [],
    }
