"""screen_image snapshot — PNG capture."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def capture(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Save pyxel.screen as a PNG with an integer scale.

    `pyxel.screen.save` appends ".png" itself, so the suffix is stripped first.
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
        # The server embeds flagged PNGs as image content after the run.
        "inline": bool(snapshot.get("inline", False)),
    }
