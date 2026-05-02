"""Resources-local helper to locate the installed Pyxel package directory.

Lives here (not in a shared `_common`) so that resource modules stay
self-contained under `_resources/`. Returns None if Pyxel cannot be imported,
allowing register() to degrade gracefully.
"""
from __future__ import annotations

import os
from typing import Optional


def pyxel_dir() -> Optional[str]:
    """Return the path of the installed pyxel module, or None if unavailable."""
    try:
        import pyxel
    except ImportError:
        return None
    return os.path.dirname(pyxel.__file__)
