"""`pyxel://anti-patterns` resource — agent-readable catalog of detector
categories surfaced by the `validate` tool.

The `validate` tool reports each anti-pattern by `category` string only.
Without rationale + fix, a category name is just a label — agents need to
know *why* the pattern is flagged and *what the canonical fix looks like*.

Source of truth for these rows is
`src/pyxel_mcp/_harnesses/tools/validate.py`. If a detector's category
string changes, update the row here as well.
"""
from __future__ import annotations


# (category, severity, rationale, fix) per detector.
# Order mirrors `_DETECTORS` in validate.py for easy cross-reference.
_ROWS: list[tuple[str, str, str, str]] = [
    (
        "missing_colkey",
        "warning",
        "pyxel.blt without colkey= renders the sprite's index-0 background as opaque pixels.",
        "Pass colkey=0 (or your transparent index) to blt(); make this the default for all sprite draws.",
    ),
    (
        "update_in_draw",
        "warning",
        "Mutating self.X inside draw() couples logic to render cadence and breaks frame skip.",
        "Move the assignment to update(); draw() should be a pure function of state.",
    ),
    (
        "tilemap_zero_zero",
        "warning",
        "Tilemap data referencing source tile (0,0) makes every uninitialized cell render that tile, flooding the map.",
        "Reserve source-bank (0,0) as a fully transparent 8x8 tile; route real content to (1,0) or beyond.",
    ),
    (
        "assets_in_update",
        "warning",
        "Calling images[N].set/load or tilemaps[N].set inside update()/draw() reloads assets every frame.",
        "Move asset loading to __init__ or a one-shot setup helper called before pyxel.run().",
    ),
    (
        "iter_modify",
        "warning",
        "Calling .append/.remove/.pop/.insert/.clear/.extend on a list while iterating it skips or doubles entries.",
        "Iterate a copy (for x in lst[:]:) or collect indices to remove and apply after the loop.",
    ),
    (
        "btn_one_shot",
        "info",
        "pyxel.btn(K) re-fires every frame the key is held — wrapping pyxel.play() in btn() retriggers the SE per frame.",
        "Use pyxel.btnp(K) for one-shot triggers (sounds, scene transitions, jumps).",
    ),
    (
        "palette_animation",
        "warning",
        "pyxel.colors[N] = X inside a for/while loop body mutates the global palette every frame.",
        "Use pyxel.pal() for per-draw color remap, or compute the palette once outside the loop.",
    ),
    (
        "cls_missing",
        "warning",
        "Calling any pixel-emitting API (blt, bltm, pset, line, rect, rectb, circ, circb, tri, trib, text) before pyxel.cls() in draw() leaves last frame's pixels behind, producing ghost trails.",
        "Make pyxel.cls(BG) the first statement of draw() (only assignments, conditional return, pal/dither calls may precede it).",
    ),
    (
        "degree_radian_mix",
        "warning",
        "math.sin/cos take radians; pyxel.sin/cos take degrees. Using both in the same module silently produces wrong angles.",
        "Pick one convention per module; if you need both, convert explicitly with math.radians/degrees at the boundary.",
    ),
]


_HEADER = "# Pyxel anti-patterns detected by `validate`"

_PREAMBLE = (
    "Each row corresponds to one detector category in the `validate` tool's "
    "output. The `severity` column maps to the `severity` field of each "
    "issue dict; rationale and fix are agent-facing context not present in "
    "the per-issue payload (which only carries `severity`, `line`, `col`, "
    "`category`, and a short `message`).\n"
)

_TABLE_HEAD = (
    "| Category | Severity | Rationale | Fix |\n"
    "|----------|----------|-----------|-----|"
)


def _format_table() -> str:
    lines = [_HEADER, "", _PREAMBLE, _TABLE_HEAD]
    for cat, sev, rationale, fix in _ROWS:
        # Pipe characters in cell content would break the table; escape them.
        cells = [
            cat,
            sev,
            rationale.replace("|", "\\|"),
            fix.replace("|", "\\|"),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def register(mcp):
    @mcp.resource(
        "pyxel://anti-patterns",
        name="Pyxel Anti-Patterns",
        description=(
            "Catalog of anti-pattern categories the `validate` tool detects, "
            "with severity, rationale, and canonical fix per category."
        ),
        mime_type="text/markdown",
    )
    def _read() -> str:
        return _format_table()
