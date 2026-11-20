"""screen_image snapshot — PNG capture."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image


def capture(
    snapshot: dict[str, Any], *, image: Image.Image | None = None
) -> dict[str, Any]:
    """Save pyxel.screen as a PNG with an integer scale.

    A saved image preserves a completed frame if a later draw is interrupted.
    """
    import pyxel

    out_path = Path(snapshot["output"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    scale = int(snapshot.get("scale", 1))

    if image is None:
        pyxel.screen.save(str(out_path), scale)
        size = [pyxel.width * scale, pyxel.height * scale]
    else:
        size = [image.width * scale, image.height * scale]
        if scale != 1:
            image = image.resize(tuple(size), resample=Image.Resampling.NEAREST)
        image.save(out_path, format="PNG")

    return {
        "frame": snapshot["frame"],
        "kind": "screen_image",
        "path": str(out_path.resolve()),
        "size": size,
        # The server embeds flagged PNGs as image content after the run.
        "inline": bool(snapshot.get("inline", False)),
    }
