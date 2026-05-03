"""Layer 3 — workflow content (skill/ md files).

The single source of truth lives at the repo root in `skill/` and is
edited there. `pyproject.toml`'s hatch build hook copies the tree into
`src/pyxel_mcp/workflow/_content/` at wheel/sdist build time so the
content ships inside the installed package — i.e., users who install via
`uvx pyxel-mcp` or `pip install pyxel-mcp` get the workflow files
without a separate clone.

Server-side, `_resources/__init__.py` walks `workflow_root()` and
registers every md file as a `pyxel://workflow/*` MCP resource. This is
the **MCP channel** of the 1-source / 2-channel publish model. The
**host skill channel** is implemented separately (`uvx pyxel-mcp
publish-skill`, Phase 5) and reads from the same `workflow_root()`.

`workflow_root()` resolves to whichever path actually exists:
- Built install: `src/pyxel_mcp/workflow/_content/` (the build hook output).
- Editable install (`pip install -e .`): repo-root `skill/` (no build hook
  has run, so `_content/` is absent — fall back to the source dir).
"""
from __future__ import annotations
from pathlib import Path

_HERE = Path(__file__).parent


def workflow_root() -> Path:
    """Return the directory that contains the workflow markdown files.

    Prefers the build-copied `_content/` (production); falls back to the
    repo-root `skill/` directory (development checkout). Raises a
    RuntimeError with both candidate paths if neither resolves.
    """
    content = _HERE / "_content"
    if content.is_dir() and (content / "SKILL.md").is_file():
        return content
    # Walk up: src/pyxel_mcp/workflow/__init__.py → src/pyxel_mcp/workflow
    # → src/pyxel_mcp → src → repo-root
    repo_root = _HERE.parent.parent.parent
    fallback = repo_root / "skill"
    if fallback.is_dir() and (fallback / "SKILL.md").is_file():
        return fallback
    raise RuntimeError(
        f"workflow content not found at {content} or {fallback}"
    )


def list_workflow_files() -> list[Path]:
    """Return all .md files under `workflow_root()`, recursive, sorted."""
    return sorted(workflow_root().rglob("*.md"))
