"""Hatch custom build hook — embed skill/ into the wheel.

The skill/ directory at the repo root is the editable source-of-truth
for the workflow content layer (Layer 3). At wheel/sdist build time
this hook copies the entire tree into
`src/pyxel_mcp/workflow/_content/` so the already-configured
`[tool.hatch.build.targets.wheel]` packages = ["src/pyxel_mcp"] target
picks it up automatically — no separate inclusion rule needed.

Hatch's custom-hook loader uses `dir()` introspection on the imported
module to find a `BuildHookInterface` subclass. Hiding the class behind
`__getattr__` (a previous workaround for venvs without hatchling) made
that introspection fail, so the hook is now defined directly. Hatchling
is always available in PEP-517 build contexts (it's listed in
`[build-system].requires`) and the local test venv installs it
explicitly.
"""
from __future__ import annotations
import shutil
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


def copy_skill_to_content(repo_root: Path) -> None:
    """Copy `<repo_root>/skill/` → `<repo_root>/src/pyxel_mcp/workflow/_content/`.

    Idempotent: any existing `_content/` is removed first. No-op when
    `skill/` itself is missing (e.g. a stripped sdist).
    """
    src = repo_root / "skill"
    dst = repo_root / "src" / "pyxel_mcp" / "workflow" / "_content"
    if not src.is_dir():
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


class CustomBuildHook(BuildHookInterface):
    """Copies repo-root skill/ → src/pyxel_mcp/workflow/_content/ pre-build,
    then removes the staged copy after the artifact is written.

    Cleaning up in `finalize()` matters when the build runs against the
    real source tree (no PEP-517 isolation copy): without it, the next
    dev run sees `_content/` and `workflow_root()` resolves to the
    stale copy instead of the canonical `skill/` directory the user is
    actually editing. The wheel itself is unaffected because the file
    contents are already inside the artefact by `finalize()` time.
    """
    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict) -> None:
        copy_skill_to_content(Path(self.root))

    def finalize(self, version: str, build_data: dict, artifact_path: str) -> None:
        dst = Path(self.root) / "src" / "pyxel_mcp" / "workflow" / "_content"
        if dst.exists():
            shutil.rmtree(dst)
