"""Hatch custom build hook — embed skill/ into the wheel.

The skill/ directory at the repo root is the editable source-of-truth for
the workflow content layer (Layer 3). At wheel/sdist build time this hook
copies the entire tree into `src/pyxel_mcp/workflow/_content/` so the
already-configured `[tool.hatch.build.targets.wheel]` packages =
["src/pyxel_mcp"] target picks it up automatically — no separate
inclusion rule needed.

`workflow_root()` (in `pyxel_mcp.workflow.__init__`) prefers the embedded
`_content/` directory over the development fallback (repo-root `skill/`),
so installed users see the bundled copy and editable-install developers
keep editing the canonical one.

Hatchling is a build-time dependency (provided by PEP 517's build
isolation) — not installed in this project's venv. To stay
unit-testable, the actual `BuildHookInterface` subclass is constructed
lazily on first attribute access via `__getattr__`. The pure copy logic
lives in `copy_skill_to_content()` and is exercised directly by tests.
"""
from __future__ import annotations
import shutil
from pathlib import Path


def copy_skill_to_content(repo_root: Path) -> None:
    """Copy `<repo_root>/skill/` → `<repo_root>/src/pyxel_mcp/workflow/_content/`.

    Idempotent: any existing `_content/` is removed first. No-op when
    `skill/` itself is missing (e.g., a stripped sdist).
    """
    src = repo_root / "skill"
    dst = repo_root / "src" / "pyxel_mcp" / "workflow" / "_content"
    if not src.is_dir():
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _build_hook_class():
    """Lazily import hatchling and construct the hook class.

    Called from `__getattr__('CustomBuildHook')` so importing this module
    in a venv without hatchling (e.g., the test runner) doesn't fail.
    """
    from hatchling.builders.hooks.plugin.interface import BuildHookInterface

    class CustomBuildHook(BuildHookInterface):
        PLUGIN_NAME = "custom"

        def initialize(self, version: str, build_data: dict) -> None:
            copy_skill_to_content(Path(self.root))

    return CustomBuildHook


def __getattr__(name: str):
    if name == "CustomBuildHook":
        return _build_hook_class()
    raise AttributeError(name)
