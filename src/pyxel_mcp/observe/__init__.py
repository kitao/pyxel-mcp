"""Observation primitives.

Wraps the `_harnesses/` subtree (subprocess-isolated tools that
read raw Pyxel state). Re-exports nothing yet; consumers import from
`pyxel_mcp.observe._harnesses.*` paths directly. Quality verification
of these observations is the agent's responsibility — the agent
asserts predicates directly in Python and inspects captured artifacts.
"""
