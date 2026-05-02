"""pyxel_info() — discovery (spec §8.2)."""
from __future__ import annotations
import sys
from importlib.metadata import PackageNotFoundError, version as _pkg_version
from pathlib import Path
from typing import Any

from pyxel_mcp._harnesses._common.error_capture import make_validation_error


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
    # top-level *.py only; subdirectory examples (if any future Pyxel ships them) are unsupported
    for path in sorted(examples_dir.glob("*.py")):
        out.append({"name": path.stem, "path": str(path), "description": None})
    return out


def _safe_version(pkg: str, errors: list[dict[str, Any]]) -> str:
    try:
        return _pkg_version(pkg)
    except PackageNotFoundError as e:
        errors.append(make_validation_error(f"package metadata not found: {pkg}: {e}"))
        return "unknown"


def run(payload: dict[str, Any]) -> dict[str, Any]:
    """Return version + resource discovery info. Degrades gracefully on broken envs.

    If `import pyxel` fails or `importlib.metadata` cannot find a package, we
    report it through the `errors` channel rather than letting the exception
    bubble to main.py's catch-all (which would mislabel the phase as
    `script_import` — pyxel_info has no script context).
    """
    errors: list[dict[str, Any]] = []
    try:
        stubs = _stubs_path()
        examples = _examples()
    except ImportError as e:
        stubs = ""
        examples = []
        errors.append(make_validation_error(f"pyxel module import failed: {e}"))

    return {
        "pyxel_mcp_version": _safe_version("pyxel-mcp", errors),
        "pyxel_version": _safe_version("pyxel", errors),
        "python_version": sys.version.split()[0],
        "stubs_path": stubs,
        "examples": examples,
        "resources": {
            "api_reference": "pyxel://api-reference",
            "user_guide": "pyxel://user-guide",
            "mml_commands": "pyxel://mml-commands",
            "pyxres_format": "pyxel://pyxres-format",
            "default_palette": "pyxel://palette/default",
            "examples": "pyxel://examples/<name>",
            "run_snapshots_schema": "pyxel://run-snapshots-schema",
            "anti_patterns": "pyxel://anti-patterns",
        },
        "errors": errors,
    }
