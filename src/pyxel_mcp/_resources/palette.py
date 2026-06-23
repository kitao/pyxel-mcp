"""Pyxel default palette as a markdown reference resource."""

# Canonical Pyxel default palette: idx → (name, RGB).
# RGB values match `pyxel.colors` at runtime (Pyxel 2.9.4); names follow the
# common-use vocabulary used elsewhere in pyxel-mcp instructions/analysis.
PALETTE: dict[int, tuple[str, tuple[int, int, int]]] = {
    0: ("black", (0, 0, 0)),
    1: ("navy", (43, 51, 95)),
    2: ("purple", (126, 32, 114)),
    3: ("green", (25, 149, 156)),
    4: ("brown", (139, 72, 82)),
    5: ("darkblue", (57, 92, 152)),
    6: ("lightblue", (169, 193, 255)),
    7: ("white", (238, 238, 238)),
    8: ("red", (212, 24, 108)),
    9: ("orange", (211, 132, 65)),
    10: ("yellow", (233, 195, 91)),
    11: ("lightgreen", (112, 198, 169)),
    12: ("cyan", (118, 150, 222)),
    13: ("lavender", (163, 163, 163)),
    14: ("pink", (255, 151, 152)),
    15: ("peach", (237, 199, 176)),
}

# Common-use hints for the agent-readable palette resource.
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
