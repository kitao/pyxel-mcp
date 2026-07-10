"""Resource registration coverage: every URI advertised by pyxel_info must
be live in `mcp.list_resources()`, and each resource must read non-empty content.

Live-fetched docs are mocked at the urlopen layer to keep the suite offline-safe.
"""
from __future__ import annotations

import io
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from pyxel_mcp.server import mcp, pyxel_info as pyxel_info_tool


# Slugs that pyxel_info advertises as live URIs (not the `examples/<name>` template).
_EXPECTED_FIXED_URIS = {
    "pyxel://api-reference",
    "pyxel://user-guide",
    "pyxel://mml-commands",
    "pyxel://pyxres-format",
    "pyxel://palette/default",
    "pyxel://run-snapshots-schema",
    "pyxel://anti-patterns",
}

_DOC_SLUGS = ("api-reference", "user-guide", "mml-commands", "pyxres-format")


@contextmanager
def _stub_urlopen():
    """Replace urlopen with a tiny in-memory responder so docs.py never hits the network."""

    class _FakeResp:
        def __init__(self, body: bytes):
            self._body = body

        def read(self):
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def _fake(url, timeout=None):
        return _FakeResp(b"# stub doc\nLive-fetch placeholder for tests.\n")

    with patch("pyxel_mcp._resources.docs.urlopen", _fake):
        yield


async def test_pyxel_info_uris_are_registered():
    """Every fixed URI in pyxel_info().resources must appear in list_resources()."""
    info = pyxel_info_tool()
    advertised = {
        info["resources"]["api_reference"],
        info["resources"]["user_guide"],
        info["resources"]["mml_commands"],
        info["resources"]["pyxres_format"],
        info["resources"]["default_palette"],
        info["resources"]["run_snapshots_schema"],
        info["resources"]["anti_patterns"],
    }
    assert advertised == _EXPECTED_FIXED_URIS

    resources = await mcp.list_resources()
    registered = {str(r.uri) for r in resources}

    missing = advertised - registered
    assert not missing, f"pyxel_info advertises URIs that aren't registered: {missing}"

    # examples are advertised as a template `pyxel://examples/<name>` — verify at
    # least one concrete example resource exists, satisfying the 8th category.
    assert any(uri.startswith("pyxel://examples/") for uri in registered), \
        "no example resources registered"

    assert "workflow" not in info["resources"]
    assert "workflow_strict_mode" not in info["resources"]
    assert "workflow_pyxel_notes" not in info["resources"]

    # Distinct categories: docs + palette + examples + schema + anti-patterns.
    categories = _EXPECTED_FIXED_URIS | {"pyxel://examples/<any>"}
    assert len(categories) >= 8


async def test_anti_patterns_resource_reads_nonempty():
    """The anti-patterns resource returns a markdown table covering every
    detector category surfaced by `validate`."""
    result = await mcp.read_resource("pyxel://anti-patterns")
    blobs = list(result)
    assert blobs and blobs[0].content
    text = blobs[0].content
    # Header + table columns
    assert "Pyxel anti-patterns" in text
    assert "Category" in text and "Severity" in text
    # Every detector category from validate.py must have a row.
    expected = {
        "anti_pattern.missing_colkey", "anti_pattern.update_in_draw",
        "anti_pattern.tilemap_zero_zero", "anti_pattern.assets_in_update",
        "anti_pattern.iter_modify", "anti_pattern.btn_one_shot",
        "anti_pattern.palette_animation", "anti_pattern.cls_missing",
        "anti_pattern.degree_radian_mix", "anti_pattern.ragged_image_set",
    }
    categories = {
        line.split("|")[1].strip()
        for line in text.splitlines()
        if line.startswith("| anti_pattern.")
    }
    assert categories == expected


async def test_palette_resource_reads_nonempty():
    result = await mcp.read_resource("pyxel://palette/default")
    blobs = list(result)
    assert blobs and blobs[0].content
    text = blobs[0].content
    # Sanity: includes header + at least one palette row.
    assert "Pyxel Default Palette" in text
    assert "black" in text and "peach" in text


async def test_run_snapshots_schema_resource_reads_nonempty():
    result = await mcp.read_resource("pyxel://run-snapshots-schema")
    blobs = list(result)
    assert blobs and blobs[0].content
    assert "snapshot" in blobs[0].content.lower()


async def test_workflow_resource_is_not_registered():
    resources = await mcp.list_resources()
    registered = {str(r.uri) for r in resources}
    assert not any(uri.startswith("pyxel://workflow") for uri in registered)


async def test_examples_resource_reads_nonempty():
    """Read whichever Pyxel example is present in the installed env."""
    resources = await mcp.list_resources()
    example_uris = [str(r.uri) for r in resources if str(r.uri).startswith("pyxel://examples/")]
    if not example_uris:
        pytest.skip("Pyxel examples not present in this install")
    result = await mcp.read_resource(example_uris[0])
    blobs = list(result)
    assert blobs and blobs[0].content
    # Sanity: example scripts import pyxel.
    assert "pyxel" in blobs[0].content


@pytest.mark.parametrize("slug", _DOC_SLUGS)
async def test_docs_resource_reads_nonempty(slug):
    """docs.py live-fetches GitHub; mock urlopen so the test is offline-safe."""
    with _stub_urlopen():
        # Bypass the doc cache so the mock actually drives the fetch path.
        from pyxel_mcp._resources import docs as docs_mod
        docs_mod._CACHE.clear()
        result = await mcp.read_resource(f"pyxel://{slug}")
        blobs = list(result)
        assert blobs and blobs[0].content
        assert "stub doc" in blobs[0].content


@pytest.mark.parametrize("slug", _DOC_SLUGS)
async def test_docs_resource_first_fetch_failure_returns_markdown(slug):
    from pyxel_mcp._resources import docs as docs_mod

    def _fail(url, timeout=None):
        raise OSError("offline")

    with patch("pyxel_mcp._resources.docs.urlopen", _fail):
        docs_mod._CACHE.clear()
        result = await mcp.read_resource(f"pyxel://{slug}")
        blobs = list(result)
        assert blobs and blobs[0].content
        assert "documentation unavailable" in blobs[0].content.lower()
