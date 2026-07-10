"""screen_image snapshot — PNG capture."""
from __future__ import annotations
from pathlib import Path
from typing import Any


def capture(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Save pyxel.screen as PNG with optional integer scale.

    pyxel.screen.save(filename, scale) appends ".png" automatically when the
    extension is absent; Pyxel 2.9.4 also normalises "foo.png" → "foo.png"
    (no double extension).  We strip a caller-supplied ".png" suffix as a
    safety measure so behaviour is identical regardless of Pyxel patch level.
    """
    import pyxel

    out_path = Path(snapshot["output"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    scale = int(snapshot.get("scale", 1))

    # Strip .png before passing to save() — Pyxel appends it automatically.
    base = out_path.with_suffix("") if out_path.suffix.lower() == ".png" else out_path
    pyxel.screen.save(str(base), scale)

    return {
        "frame": snapshot["frame"],
        "kind": "screen_image",
        "path": str(out_path.resolve()),
        "size": [pyxel.width * scale, pyxel.height * scale],
    }
