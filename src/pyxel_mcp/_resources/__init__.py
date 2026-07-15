"""MCP resource registration aggregator."""
from __future__ import annotations

from pathlib import Path

from pyxel_mcp._resources import examples, palette, validation_patterns


def _register_run_snapshots_schema(mcp) -> None:
    """Register the static run snapshot schema markdown resource."""
    schema_path = Path(__file__).parent / "run-snapshots-schema.md"

    @mcp.resource(
        "pyxel://run-snapshots-schema",
        name="Run Snapshots Schema",
        description="Full snapshot schema reference for the run tool's snapshots parameter.",
        mime_type="text/markdown",
    )
    def _read() -> str:
        return schema_path.read_text()


def register_resources(mcp) -> None:
    """Register all MCP resources on the given FastMCP instance."""
    _register_run_snapshots_schema(mcp)
    palette.register(mcp)
    examples.register(mcp)
    validation_patterns.register(mcp)
