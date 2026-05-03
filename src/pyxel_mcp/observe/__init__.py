"""Layer 1 — observe primitives.

Wraps the original `_harnesses/` subtree (subprocess-isolated tools that
read raw Pyxel state). Re-exports nothing yet; consumers import from
`pyxel_mcp.observe._harnesses.*` paths directly. The split exists so that
Layer 2 (`pyxel_mcp.judge`) can stand on its own without dragging in any
Pyxel-touching modules.
"""
