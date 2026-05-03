"""Tests for resilience and description-cleanup of workflow resources.

P0-4: server must still start when `workflow_root()` raises.
P1-8: description must skip YAML front matter and strip control chars.
"""
from __future__ import annotations
from typing import Any

import pytest

from pyxel_mcp._resources import (
    _first_paragraph,
    _register_workflow,
    _strip_yaml_front_matter,
)


class _MockMCP:
    def __init__(self):
        self.resources: dict[str, dict[str, Any]] = {}

    def resource(self, uri, name=None, description=None, mime_type=None):
        def decorator(fn):
            self.resources[uri] = {
                "name": name, "description": description,
                "mime_type": mime_type, "fn": fn,
            }
            return fn
        return decorator


# ---------- P0-4: register_workflow tolerates missing content ------------

def test_register_workflow_survives_runtime_error(monkeypatch, capsys):
    import pyxel_mcp.workflow as wf

    def boom():
        raise RuntimeError("workflow content not found")

    monkeypatch.setattr(wf, "workflow_root", boom)
    monkeypatch.setattr(wf, "list_workflow_files", boom)

    mcp = _MockMCP()
    # Must NOT raise — the server has to keep coming up.
    _register_workflow(mcp)

    # No workflow URIs were registered (graceful degradation).
    assert not any(uri.startswith("pyxel://workflow") for uri in mcp.resources)

    # A diagnostic line surfaced on stderr.
    err = capsys.readouterr().err
    assert "workflow content unavailable" in err
    assert "workflow content not found" in err


# ---------- P1-8: YAML front matter stripping ----------------------------

def test_strip_yaml_front_matter_removes_metadata():
    src = "---\nname: foo\ndescription: bar\n---\n# Heading\n\nBody paragraph.\n"
    out = _strip_yaml_front_matter(src)
    assert out.startswith("# Heading")
    assert "name: foo" not in out


def test_strip_yaml_front_matter_passes_through_when_absent():
    src = "# Heading\n\nBody.\n"
    assert _strip_yaml_front_matter(src) == src


def test_strip_yaml_front_matter_passes_through_unterminated_block():
    """Malformed front matter (no closing `---`) is left in place."""
    src = "---\nstray\nno closing fence here either\n"
    assert _strip_yaml_front_matter(src) == src


def test_first_paragraph_skips_front_matter():
    src = (
        "---\n"
        "name: pyxel\n"
        "description: this is the metadata description\n"
        "---\n"
        "# Pyxel Workflow\n"
        "\n"
        "First real paragraph of the document.\n"
    )
    desc = _first_paragraph(src)
    assert "name: pyxel" not in desc
    assert "metadata description" not in desc
    assert "Pyxel Workflow" in desc or "First real paragraph" in desc


def test_first_paragraph_strips_control_chars():
    src = "Heading with \x01\x02 ctrl chars in middle\n\nBody."
    out = _first_paragraph(src)
    # Ctrl chars are replaced with spaces (not removed) so visible offsets
    # stay roughly the same — agents reading the description won't see raw
    # \x01.
    assert "\x01" not in out
    assert "\x02" not in out


# ---------- regression: registered resources still work after fixes ------

def test_workflow_resources_register_when_content_present():
    """Smoke check that the happy path still works after the resilience patch."""
    mcp = _MockMCP()
    _register_workflow(mcp)
    assert "pyxel://workflow" in mcp.resources
    skill_desc = mcp.resources["pyxel://workflow"]["description"]
    # Now it should be content, not the YAML metadata.
    assert "name: pyxel" not in skill_desc
    assert "description:" not in skill_desc.lower()[:40]
