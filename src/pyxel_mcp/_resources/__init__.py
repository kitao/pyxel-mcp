"""MCP resource registration aggregator."""
from __future__ import annotations

import sys
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


def _strip_yaml_front_matter(text: str) -> str:
    """Drop a leading `---\\n...\\n---\\n` block, if present.

    Skill md files (notably SKILL.md) start with a YAML metadata block.
    Without stripping it, the resource description would surface
    `name: pyxel\\ndescription: …` as the user-visible blurb instead of
    the actual lead paragraph.
    """
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    if end < 0:
        return text
    return text[end + len("\n---\n"):]


def _first_paragraph(text: str, limit: int = 200) -> str:
    """Return the first non-empty paragraph (≤ limit chars) of `text`,
    after skipping any YAML front matter.

    Control characters are replaced with spaces so the description is
    safe to surface in MCP clients that don't sanitise resource metadata.
    """
    body = _strip_yaml_front_matter(text)
    for chunk in body.split("\n\n"):
        chunk = chunk.strip()
        if chunk:
            sanitised = "".join(
                c if c.isprintable() or c == " " else " " for c in chunk
            )
            return sanitised[:limit]
    return ""


def _register_workflow(mcp) -> None:
    """Walk `workflow_root()` and register each md file as an MCP resource.

    Layer 3 (skill/) is published over MCP via the `pyxel://workflow/*`
    URI namespace. SKILL.md becomes the bare `pyxel://workflow` entry
    point; sub-paths mirror the on-disk layout (`knowledge/pixel-art.md`
    → `pyxel://workflow/knowledge/pixel-art`).

    If `workflow_root()` raises (the wheel was built without the build
    hook running, or `skill/` is absent in a development tree), we log
    one stderr line and return — the server still starts and the rest
    of the resource surface (anti-patterns, examples, etc.) remains
    available. The agent will see no `pyxel://workflow/*` resources but
    can still drive Layer 1 / Layer 2 tools.
    """
    from pyxel_mcp.workflow import list_workflow_files, workflow_root
    try:
        root = workflow_root()
        files = list_workflow_files()
    except RuntimeError as e:
        sys.stderr.write(
            "[pyxel-mcp] warning: workflow content unavailable, "
            f"pyxel://workflow/* resources will not be registered ({e})\n"
        )
        return
    for md_path in files:
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
