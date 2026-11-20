"""Convert palette indices to RGB using Pyxel's display rules."""

import numpy as np
from PIL import Image
from pyxel import colors as engine_colors


def rgb_image(indices: np.ndarray) -> Image.Image:
    # The original palette proxy remains live even if a script rebinds pyxel.colors.
    # The display and Image.save clamp out-of-palette indices to the last color.
    palette = np.array(
        [list(color.to_bytes(3, "big")) for color in engine_colors], dtype=np.uint8
    )
    return Image.fromarray(palette[np.minimum(indices, len(palette) - 1)])
