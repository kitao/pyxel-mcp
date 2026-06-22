"""Tests for workflow MCP resource registration.

`_register_workflow(mcp)` walks `workflow_root()` and registers every
md file (except README.md) as a `pyxel://workflow/*` resource. SKILL.md
is special-cased to live at the bare `pyxel://workflow` URI.
"""
from __future__ import annotations
from typing import Any

import pytest

from pyxel_mcp._resources import _register_workflow
from pyxel_mcp.workflow import workflow_root


class _MockMCP:
    """Captures @mcp.resource() registrations for inspection."""
    def __init__(self):
        self.resources: dict[str, dict[str, Any]] = {}

    def resource(self, uri, name=None, description=None, mime_type=None):
        def decorator(fn):
            self.resources[uri] = {
                "name": name,
                "description": description,
                "mime_type": mime_type,
                "fn": fn,
            }
            return fn
        return decorator


@pytest.fixture
def mcp():
    m = _MockMCP()
    _register_workflow(m)
    return m


def test_skill_md_at_root_uri(mcp):
    """SKILL.md is the entry point — exposed at the bare workflow URI."""
    assert "pyxel://workflow" in mcp.resources


def test_lean_workflow_files_are_registered(mcp):
    """The bundled skill exposes a small default surface plus opt-in strict notes."""
    expected = {
        "pyxel://workflow",
        "pyxel://workflow/strict-mode",
        "pyxel://workflow/pyxel-notes",
    }
    missing = expected - set(mcp.resources)
    assert not missing


def test_stage_and_knowledge_resources_are_not_registered(mcp):
    """The old 7-stage harness is intentionally absent from the default resources."""
    forbidden_fragments = (
        "visual-target", "decomposer", "scaffold", "asset-planner",
        "asset-gen", "task-execution", "quality-gate", "knowledge/",
        "test-harness", "capture", "quirks",
    )
    offenders = [uri for uri in mcp.resources if any(f in uri for f in forbidden_fragments)]
    assert offenders == []


def test_readme_is_not_registered(mcp):
    """README.md is repo housekeeping, not workflow content."""
    assert "pyxel://workflow/README" not in mcp.resources
    assert "pyxel://workflow/readme" not in mcp.resources


def test_resource_handler_returns_file_content(mcp):
    """Calling the registered handler returns the actual md file's content."""
    handler = mcp.resources["pyxel://workflow"]["fn"]
    content = handler()
    assert isinstance(content, str)
    assert "# pyxel" in content
    assert "## Default Loop" in content


def test_each_resource_has_mime_type_text_markdown(mcp):
    for uri, meta in mcp.resources.items():
        assert meta["mime_type"] == "text/markdown", uri


def test_each_resource_has_a_name(mcp):
    for uri, meta in mcp.resources.items():
        assert meta["name"], uri


def test_resource_count_matches_md_count(mcp):
    """One resource per md (excluding README.md)."""
    md_files = list((workflow_root()).rglob("*.md"))
    expected_count = sum(1 for p in md_files if p.name != "README.md")
    assert len(mcp.resources) == expected_count
