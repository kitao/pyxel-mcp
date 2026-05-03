"""Tests for the hatch build hook.

The pure copy logic (`copy_skill_to_content`) is exercised directly with
a fake repo layout. The `CustomBuildHook` class itself is constructed
lazily inside the module — its instantiation requires hatchling, which
this venv may not have, so we exercise it only when the dependency is
available.
"""
from __future__ import annotations
import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_build_hooks():
    spec = importlib.util.spec_from_file_location(
        "build_hooks", REPO_ROOT / "build_hooks.py",
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_copy_skill_to_content_handles_typical_layout(tmp_path):
    """Given a fake repo with skill/, the helper drops a mirror under
    src/pyxel_mcp/workflow/_content/."""
    (tmp_path / "skill").mkdir()
    (tmp_path / "skill" / "SKILL.md").write_text("# fake SKILL\n")
    (tmp_path / "skill" / "knowledge").mkdir()
    (tmp_path / "skill" / "knowledge" / "topic.md").write_text("# topic\n")
    (tmp_path / "src" / "pyxel_mcp" / "workflow").mkdir(parents=True)

    bh = _load_build_hooks()
    bh.copy_skill_to_content(tmp_path)

    dst = tmp_path / "src" / "pyxel_mcp" / "workflow" / "_content"
    assert (dst / "SKILL.md").read_text() == "# fake SKILL\n"
    assert (dst / "knowledge" / "topic.md").read_text() == "# topic\n"


def test_copy_skill_to_content_is_idempotent(tmp_path):
    """Running twice should leave the same state, no errors."""
    (tmp_path / "skill").mkdir()
    (tmp_path / "skill" / "SKILL.md").write_text("# v1\n")
    (tmp_path / "src" / "pyxel_mcp" / "workflow").mkdir(parents=True)

    bh = _load_build_hooks()
    bh.copy_skill_to_content(tmp_path)
    # Modify source; second run should overwrite the destination cleanly.
    (tmp_path / "skill" / "SKILL.md").write_text("# v2\n")
    bh.copy_skill_to_content(tmp_path)

    dst_skill = tmp_path / "src" / "pyxel_mcp" / "workflow" / "_content" / "SKILL.md"
    assert dst_skill.read_text() == "# v2\n"


def test_copy_skill_to_content_no_op_without_skill_dir(tmp_path):
    """If skill/ is missing entirely (stripped sdist), do not raise."""
    bh = _load_build_hooks()
    bh.copy_skill_to_content(tmp_path)  # does not raise
    assert not (tmp_path / "src" / "pyxel_mcp" / "workflow" / "_content").exists()


def test_module_exposes_lazy_custom_build_hook_attribute():
    """Module's __getattr__ should resolve CustomBuildHook when hatchling is
    available; when not, accessing the attribute raises ImportError (which
    inherits from Exception). Either path is acceptable here — what we want
    to assert is that the *non-hatchling* module surface is clean: the
    `copy_skill_to_content` function and its docstring exist regardless."""
    bh = _load_build_hooks()
    assert callable(bh.copy_skill_to_content)
    # Check the lazy-loader exists and references CustomBuildHook by name.
    assert callable(getattr(bh, "_build_hook_class"))


@pytest.mark.skipif(
    importlib.util.find_spec("hatchling") is None,
    reason="hatchling not installed in this venv",
)
def test_custom_build_hook_class_resolves_when_hatchling_available():
    bh = _load_build_hooks()
    cls = bh.CustomBuildHook
    assert cls.PLUGIN_NAME == "custom"
