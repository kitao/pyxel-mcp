"""The default palette shipped with the installed Pyxel package."""


def _format_palette() -> str:
    import pyxel

    names = {getattr(pyxel, key): key for key in dir(pyxel) if key.startswith("COLOR_")}
    colors = pyxel.DEFAULT_COLORS
    rows = [
        f"# Pyxel Default Palette ({len(colors)} colors)",
        "",
        "| Index | Constant | Hex | RGB |",
        "|---:|---|---|---|",
    ]
    for index, color in enumerate(colors):
        rgb = tuple(color.to_bytes(3, "big"))
        rows.append(f"| {index} | {names.get(index, '')} | #{color:06X} | {rgb} |")
    return "\n".join(rows) + "\n"


def register(mcp):
    @mcp.resource(
        "pyxel://palette/default",
        name="Pyxel Default Palette",
        description="Installed Pyxel palette indices, COLOR_ constants and RGB values.",
        mime_type="text/markdown",
    )
    def palette() -> str:
        return _format_palette()
