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


def _srgb_channel(c):
    """Convert sRGB channel (0-255) to linear."""
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(idx):
    """WCAG 2.0 relative luminance for a palette index."""
    r, g, b = color_rgb(idx)
    return 0.2126 * _srgb_channel(r) + 0.7152 * _srgb_channel(g) + 0.0722 * _srgb_channel(b)


def wcag_contrast(c1, c2):
    """WCAG 2.0 contrast ratio between two palette indices."""
    l1 = relative_luminance(c1)
    l2 = relative_luminance(c2)
    lighter = max(l1, l2) + 0.05
    darker = min(l1, l2) + 0.05
    return lighter / darker


# 3-layer color hierarchy
_BG_COLORS = {0, 1, 5}           # Background: black, navy, dark_blue
_ENV_COLORS = {3, 4, 13}         # Environment: green, brown, gray
_INTERACTIVE_COLORS = {8, 10, 11}  # Interactive: red, yellow, lime


def classify_color(idx):
    """Classify a color into 'background', 'environment', 'interactive', or 'neutral'."""
    if idx in _BG_COLORS:
        return "background"
    if idx in _ENV_COLORS:
        return "environment"
    if idx in _INTERACTIVE_COLORS:
        return "interactive"
    return "neutral"


def analyze_hierarchy(used_colors, bg_color):
    """Analyze color usage against 3-layer hierarchy.

    Returns dict with layer counts and conformance score.
    """
    fg_colors = {c for c in used_colors if c != bg_color}
    layers = {"background": 0, "environment": 0, "interactive": 0, "neutral": 0}
    for c in fg_colors:
        layers[classify_color(c)] += 1

    # Score: good if at least 1 environment + 1 interactive color
    has_env = layers["environment"] > 0
    has_interactive = layers["interactive"] > 0
    score = (1 if has_env else 0) + (1 if has_interactive else 0)

    return {
        "layers": layers,
        "fg_count": len(fg_colors),
        "score": score,  # 0-2
        "has_environment": has_env,
        "has_interactive": has_interactive,
    }
