"""Pyxel default palette as a markdown reference resource."""

from pyxel_mcp._common.palette import PALETTE

# Common-use hints — informed by 142-game analysis (see instructions.md).
_USE_HINTS = {
    0: "bg, outline",
    1: "dark bg, shadows",
    2: "dark accent, magic",
    3: "ground, foliage",
    4: "wood, dirt, skin shadow",
    5: "stone, twilight",
    6: "sky, water",
    7: "highlight, mid bg",
    8: "blood, danger",
    9: "fire, orange",
    10: "highlight, gold",
    11: "grass, success",
    12: "water, ice",
    13: "metal, fog",
    14: "skin, soft accent",
    15: "skin highlight, light",
}


def _format_palette() -> str:
    rows = ["# Pyxel Default Palette (16 colors)", ""]
    rows.append("| Idx | Name      | Hex      | RGB           | Common use |")
    rows.append("|-----|-----------|----------|---------------|------------|")
    for idx, (name, rgb) in PALETTE.items():
        hex_ = "#{:02X}{:02X}{:02X}".format(*rgb)
        rgb_str = f"({rgb[0]:>3}, {rgb[1]:>3}, {rgb[2]:>3})"
        use = _USE_HINTS.get(idx, "")
        rows.append(f"| {idx:<3} | {name:<9} | {hex_:<8} | {rgb_str:<13} | {use} |")
    return "\n".join(rows) + "\n"


def register(mcp):
    @mcp.resource(
        "pyxel://palette/default",
        name="Pyxel Default Palette",
        description="Pyxel's 16-color default palette with names, RGB, and use hints.",
        mime_type="text/markdown",
    )
    def palette() -> str:
        return _format_palette()
