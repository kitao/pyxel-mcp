"""Bundled Pyxel workflow skill content.

The source of truth lives at repo-root `skill/`. The Hatch build hook copies
that directory into `src/pyxel_mcp/workflow/_content/` for wheels, while editable
checkouts read the repo-root copy directly.
"""
from __future__ import annotations
from pathlib import Path

_HERE = Path(__file__).parent


def workflow_root() -> Path:
    """Return the directory containing bundled skill markdown files."""
    content = _HERE / "_content"
    if content.is_dir() and (content / "SKILL.md").is_file():
        return content
    repo_root = _HERE.parent.parent.parent
    fallback = repo_root / "skill"
    if fallback.is_dir() and (fallback / "SKILL.md").is_file():
        return fallback
    raise RuntimeError(
        f"workflow content not found at {content} or {fallback}"
    )


def list_workflow_files() -> list[Path]:
    """Return all markdown files under `workflow_root()`, recursively sorted."""
    return sorted(workflow_root().rglob("*.md"))
