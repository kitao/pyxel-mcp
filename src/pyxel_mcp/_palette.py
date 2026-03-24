"""Pyxel color palette data and utilities."""

PALETTE = {
    0: ("black", (0, 0, 0)),
    1: ("navy", (43, 51, 95)),
    2: ("purple", (126, 32, 114)),
    3: ("green", (25, 149, 56)),
    4: ("brown", (139, 72, 82)),
    5: ("dark_blue", (57, 92, 152)),
    6: ("light_blue", (169, 193, 255)),
    7: ("white", (238, 238, 238)),
    8: ("red", (212, 24, 108)),
    9: ("orange", (211, 132, 65)),
    10: ("yellow", (233, 195, 91)),
    11: ("lime", (112, 198, 169)),
    12: ("cyan", (118, 150, 222)),
    13: ("gray", (163, 163, 163)),
    14: ("pink", (255, 151, 152)),
    15: ("peach", (237, 199, 176)),
}


def color_name(idx):
    """Return color name for a palette index, or '?' if unknown."""
    entry = PALETTE.get(idx)
    return entry[0] if entry else "?"


def color_rgb(idx):
    """Return (r, g, b) for a palette index, or (0,0,0) if unknown."""
    entry = PALETTE.get(idx)
    return entry[1] if entry else (0, 0, 0)


def luminance(idx):
    """Compute perceived luminance (0-255) for a palette index."""
    r, g, b = color_rgb(idx)
    return 0.299 * r + 0.587 * g + 0.114 * b


def color_contrast(c1, c2):
    """Luminance contrast ratio between two palette indices."""
    lum1 = luminance(c1)
    lum2 = luminance(c2)
    lighter = max(lum1, lum2) + 0.05
    darker = min(lum1, lum2) + 0.05
    return lighter / darker
