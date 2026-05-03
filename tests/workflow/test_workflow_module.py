"""Tests for the workflow content locator (Layer 3).

`workflow_root()` returns the path containing skill markdown — preferring
the build-copied `_content/` directory in installed wheels and falling
back to repo-root `skill/` during development.
"""
from __future__ import annotations
import shutil
from pathlib import Path

import pytest

from pyxel_mcp import workflow


def test_workflow_root_returns_existing_dir():
    """workflow_root() returns a directory that exists and contains SKILL.md."""
    root = workflow.workflow_root()
    assert root.is_dir()
    assert (root / "SKILL.md").is_file()


def test_workflow_root_dev_fallback_to_repo_skill():
    """In development (no _content/), the helper resolves to repo-root skill/."""
    # In this checkout there is no built _content/, so the fallback path
    # (repo-root skill/) is what should be returned.
    root = workflow.workflow_root()
    assert root.name == "skill"
    # And it should be at repo root, not under src/pyxel_mcp/workflow/
    assert "_content" not in root.as_posix()


def test_list_workflow_files_includes_known_stages():
    """list_workflow_files() should at least include the 7 pipeline stages
    + SKILL.md + 5 knowledge files."""
    files = workflow.list_workflow_files()
    names = {p.name for p in files}
    expected_subset = {
        "SKILL.md",
        "visual-target.md", "decomposer.md", "scaffold.md",
        "asset-planner.md", "asset-gen.md", "task-execution.md",
        "quality-gate.md",
        "test-harness.md", "capture.md", "quirks.md",
    }
    missing = expected_subset - names
    assert not missing, f"missing workflow files: {missing}"


def test_list_workflow_files_includes_knowledge():
    """knowledge/*.md should be discoverable via the recursive walk."""
    files = workflow.list_workflow_files()
    rels = {f.relative_to(workflow.workflow_root()).as_posix() for f in files}
    expected = {
        "knowledge/pixel-art.md",
        "knowledge/background.md",
        "knowledge/game-feel.md",
        "knowledge/audio.md",
        "knowledge/patterns.md",
    }
    missing = expected - rels
    assert not missing, f"missing knowledge files: {missing}"


def test_list_workflow_files_returns_sorted():
    """Sorted output keeps registration order stable across runs."""
    files = workflow.list_workflow_files()
    assert files == sorted(files)


def test_workflow_root_prefers_built_content(tmp_path, monkeypatch):
    """When _content/ exists with SKILL.md, it wins over the repo-root fallback."""
    # Synthesise a fake "installed" layout under tmp_path:
    fake_pkg = tmp_path / "pyxel_mcp" / "workflow"
    fake_content = fake_pkg / "_content"
    fake_content.mkdir(parents=True)
    (fake_content / "SKILL.md").write_text("# fake SKILL\n")
    (fake_pkg / "__init__.py").write_text("")
    # Point the workflow module's _HERE to the fake package
    monkeypatch.setattr(workflow, "_HERE", fake_pkg)
    root = workflow.workflow_root()
    assert root == fake_content
    assert (root / "SKILL.md").read_text() == "# fake SKILL\n"


def test_workflow_root_raises_when_neither_path_exists(tmp_path, monkeypatch):
    """If both _content/ and the repo-root fallback are missing, raise loudly."""
    fake_here = tmp_path / "deep" / "nested" / "pkg" / "workflow"
    fake_here.mkdir(parents=True)
    monkeypatch.setattr(workflow, "_HERE", fake_here)
    with pytest.raises(RuntimeError, match="workflow content not found"):
        workflow.workflow_root()
