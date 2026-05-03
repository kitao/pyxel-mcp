"""MCP resource registration aggregator."""
from __future__ import annotations

from pathlib import Path

from pyxel_mcp._resources import anti_patterns, docs, examples, palette


def _register_run_snapshots_schema(mcp) -> None:
    """Static markdown file shipped alongside this package."""
    schema_path = Path(__file__).parent / "run-snapshots-schema.md"

    @mcp.resource(
        "pyxel://run-snapshots-schema",
        name="Run Snapshots Schema",
        description="Full snapshot schema reference for the run tool's snapshots parameter.",
        mime_type="text/markdown",
    )
    def _read() -> str:
        return schema_path.read_text()


def _md_to_workflow_uri(rel: Path) -> str | None:
    """Map a workflow md file's relative path to its `pyxel://workflow/*` URI.

    Returns None when the file should not be exposed (e.g., README.md).
    """
    if rel.name == "README.md":
        return None
    stem = rel.with_suffix("")
    if stem.as_posix() == "SKILL":
        return "pyxel://workflow"
    return f"pyxel://workflow/{stem.as_posix()}"


def _make_workflow_handler(path: Path):
    """Build a closure-bound resource handler for `path`.

    Wrapping in a function gives each handler its own scope, avoiding the
    classic loop-closure binding bug.
    """
    def _read() -> str:
        return path.read_text()
    return _read


def _first_paragraph(text: str, limit: int = 200) -> str:
    """Return the first non-empty paragraph (≤ limit chars) of `text`."""
    for chunk in text.split("\n\n"):
        chunk = chunk.strip()
        if chunk:
            return chunk[:limit]
    return ""


def _register_workflow(mcp) -> None:
    """Walk `workflow_root()` and register each md file as an MCP resource.

    Layer 3 (skill/) is published over MCP via the `pyxel://workflow/*`
    URI namespace. SKILL.md becomes the bare `pyxel://workflow` entry
    point; sub-paths mirror the on-disk layout (`knowledge/pixel-art.md`
    → `pyxel://workflow/knowledge/pixel-art`).
    """
    from pyxel_mcp.workflow import list_workflow_files, workflow_root
    root = workflow_root()
    for md_path in list_workflow_files():
        rel = md_path.relative_to(root)
        uri = _md_to_workflow_uri(rel)
        if uri is None:
            continue
        name = (
            "Workflow: SKILL"
            if uri == "pyxel://workflow"
            else f"Workflow: {rel.with_suffix('').as_posix()}"
        )
        try:
            description = _first_paragraph(md_path.read_text())
        except OSError:
            description = ""
        handler = _make_workflow_handler(md_path)
        mcp.resource(
            uri, name=name, description=description, mime_type="text/markdown",
        )(handler)


def register_resources(mcp) -> None:
    """Register all MCP resources on the given FastMCP instance."""
    _register_run_snapshots_schema(mcp)
    palette.register(mcp)
    examples.register(mcp)
    docs.register(mcp)
    anti_patterns.register(mcp)
    _register_workflow(mcp)
