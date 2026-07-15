"""Direct palette observations."""

from __future__ import annotations

from typing import Any

import numpy as np


def _hex(color: int) -> str:
    return f"#{color:06x}"


def _used_indices() -> list[int]:
    import pyxel

    used: set[int] = set()
    for bank in pyxel.images:
        pixels = np.frombuffer(
            bank.data_ptr(),
            dtype=np.uint8,
            count=bank.width * bank.height,
        )
        used.update(int(value) for value in np.unique(pixels))
    return sorted(used)


def analyze_palette() -> dict[str, Any]:
    import pyxel

    colors = list(pyxel.colors)
    return {
        "colors": {index: _hex(color) for index, color in enumerate(colors)},
        "extended_palette": len(colors) > 16,
        "palette_size": len(colors),
        "used_indices": _used_indices(),
        "errors": [],
    }
