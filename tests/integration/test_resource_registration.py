"""Registration coverage for the small, local-only resource surface."""

import pytest

from pyxel_mcp.server import mcp, pyxel_info as pyxel_info_tool


_EXPECTED_FIXED_URIS = {
    "pyxel://palette/default",
    "pyxel://run-snapshots-schema",
    "pyxel://validation-patterns",
}


async def test_pyxel_info_matches_registered_resources():
    info = pyxel_info_tool()
    fixed = {
        uri for uri in info["resources"].values()
        if "{" not in uri
    }
    assert fixed == _EXPECTED_FIXED_URIS
    assert info["resources"]["examples"] == "pyxel://examples/{name}"

    resources = await mcp.list_resources()
    assert {str(resource.uri) for resource in resources} == _EXPECTED_FIXED_URIS

    templates = await mcp.list_resource_templates()
    assert {str(template.uriTemplate) for template in templates} == {
        "pyxel://examples/{name}",
    }


async def test_validation_patterns_resource_covers_every_detector_category():
    result = await mcp.read_resource("pyxel://validation-patterns")
    blobs = list(result)
    assert blobs and blobs[0].content
    text = blobs[0].content
    assert "Validation Patterns" in text
    assert "Category" in text and "Severity" in text

    expected = {
        "anti_pattern.missing_colkey",
        "anti_pattern.update_in_draw",
        "anti_pattern.tilemap_zero_zero",
        "anti_pattern.assets_in_update",
        "anti_pattern.iter_modify",
        "anti_pattern.btn_one_shot",
        "anti_pattern.palette_animation",
        "anti_pattern.cls_missing",
        "anti_pattern.degree_radian_mix",
        "anti_pattern.ragged_image_set",
    }
    categories = {
        line.split("|")[1].strip()
        for line in text.splitlines()
        if line.startswith("| anti_pattern.")
    }
    assert categories == expected


@pytest.mark.parametrize(
    ("uri", "marker"),
    [
        ("pyxel://palette/default", "Pyxel Default Palette"),
        ("pyxel://run-snapshots-schema", "snapshot"),
    ],
)
async def test_static_resource_reads_nonempty(uri, marker):
    result = await mcp.read_resource(uri)
    blobs = list(result)
    assert blobs and blobs[0].content
    assert marker.lower() in blobs[0].content.lower()


async def test_snapshot_resource_documents_chronological_result_order():
    result = await mcp.read_resource("pyxel://run-snapshots-schema")
    text = list(result)[0].content.lower()

    assert "chronological" in text
    assert "same order as the input `snapshots` list" not in text


async def test_example_template_reads_installed_example():
    examples = pyxel_info_tool()["examples"]
    if not examples:
        pytest.skip("Pyxel examples not present in this install")

    result = await mcp.read_resource(f"pyxel://examples/{examples[0]['name']}")
    blobs = list(result)
    assert blobs and blobs[0].content
    assert "pyxel" in blobs[0].content


async def test_example_template_rejects_unknown_names():
    with pytest.raises(ValueError, match="not found"):
        await mcp.read_resource("pyxel://examples/not-an-installed-example")
