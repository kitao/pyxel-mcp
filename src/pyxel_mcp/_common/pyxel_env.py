"""Pyxel installation detection, version checks, and script validation."""

import json
import os
import sys
from importlib.metadata import version as pkg_version
from importlib.util import find_spec
from urllib.request import urlopen


def pyxel_dir():
    """Find installed Pyxel package directory (without importing Pyxel)."""
    try:
        spec = find_spec("pyxel")
        if spec:
            if spec.origin:
                return os.path.dirname(spec.origin)
            if spec.submodule_search_locations:
                return list(spec.submodule_search_locations)[0]
    except ModuleNotFoundError:
        pass
    except ValueError:
        # sys.modules["pyxel"] may be a stub without __spec__ set
        # (e.g. from test mocks). Try again after temporarily removing it.
        saved = sys.modules.pop("pyxel", None)
        try:
            spec = find_spec("pyxel")
            if spec:
                if spec.origin:
                    return os.path.dirname(spec.origin)
                if spec.submodule_search_locations:
                    return list(spec.submodule_search_locations)[0]
        except (ModuleNotFoundError, ValueError):
            pass
        finally:
            if saved is not None:
                sys.modules["pyxel"] = saved
    return None


def check_script(script_path, need_pyxel=True):
    """Validate script path (and optionally Pyxel installation).

    Returns (abs_path, None) on success or (None, error_message) on failure.
    """
    if need_pyxel and not pyxel_dir():
        return None, "Pyxel is not installed. Run: pip install pyxel-mcp"
    path = os.path.abspath(script_path)
    if not os.path.isfile(path):
        return None, f"script not found: {path}"
    return path, None


def installed_version(pkg):
    """Get installed version of a package, or None."""
    try:
        return pkg_version(pkg)
    except Exception:
        return None


def parse_version(v):
    """Parse version string to comparable tuple of ints."""
    try:
        return tuple(int(x) for x in v.split(".")[:3])
    except (ValueError, AttributeError):
        return ()


def check_updates():
    """Check PyPI for newer versions of pyxel-mcp and pyxel.

    Returns list of notification strings. Empty on failure or if up to date.
    """
    notifications = []
    for pkg in ("pyxel-mcp", "pyxel"):
        try:
            installed = installed_version(pkg)
            if not installed:
                continue
            url = f"https://pypi.org/pypi/{pkg}/json"
            with urlopen(url, timeout=3) as resp:
                data = json.loads(resp.read())
            latest = data["info"]["version"]
            if parse_version(latest) > parse_version(installed):
                notifications.append(
                    f"Update available: {pkg} {installed} → {latest}"
                    f" (pip install --upgrade {pkg})"
                )
        except Exception:
            continue
    return notifications
