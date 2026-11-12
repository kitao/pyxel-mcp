"""Registration coverage for the small, local-only resource surface."""

from pathlib import Path

import pytest
from mcp.server.mcpserver.exceptions import ResourceError, ResourceNotFoundError

from pyxel_mcp._resources import examples as example_resources
from pyxel_mcp.server import mcp
from pyxel_mcp.server import pyxel_info as pyxel_info_tool
from tests.conftest import structured

_EXPECTED_FIXED_URIS = {
    "pyxel://palette/default",
    "pyxel://run-snapshots-schema",
    "pyxel://validation-patterns",
}


async def test_pyxel_info_matches_registered_resources():
    info = structured(pyxel_info_tool())
    fixed = {uri for uri in info["resources"].values() if "{" not in uri}
    assert fixed == _EXPECTED_FIXED_URIS
    assert info["resources"]["examples"] == "pyxel://examples/{name}"

    resources = await mcp.list_resources()
    assert {str(resource.uri) for resource in resources} == _EXPECTED_FIXED_URIS

    templates = await mcp.list_resource_templates()
    assert {str(template.uri_template) for template in templates} == {
        "pyxel://examples/{name}",
        "pyxel://examples/cube/{name}",
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
    text = next(iter(result)).content.lower()

    assert "chronological" in text
    assert "same order as the input `snapshots` list" not in text


async def test_example_template_reads_installed_example():
    examples = structured(pyxel_info_tool())["examples"]
    if not examples:
        pytest.skip("Pyxel examples not present in this install")

    result = await mcp.read_resource(f"pyxel://examples/{examples[0]['name']}")
    blobs = list(result)
    assert blobs and blobs[0].content
    assert "pyxel" in blobs[0].content


async def test_cube_example_resources_match_the_discovered_source_files():
    examples = structured(pyxel_info_tool())["examples"]
    cube_examples = [
        example for example in examples if example["name"].startswith("cube/")
    ]
    assert cube_examples
    for example in cube_examples:
        result = await mcp.read_resource(f"pyxel://examples/{example['name']}")
        text = next(iter(result)).content
        assert text == Path(example["path"]).read_text(encoding="utf-8")
        assert "from pyxel.cube import" in text


@pytest.mark.parametrize("prefix", ["", "cube/"])
async def test_example_template_rejects_unknown_names(prefix):
    with pytest.raises(ResourceError, match="not found"):
        await mcp.read_resource(f"pyxel://examples/{prefix}not-an-installed-example")


@pytest.mark.parametrize("prefix", ["", "cube/"])
async def test_example_template_rejects_path_traversal(prefix):
    with pytest.raises(ResourceNotFoundError):
        await mcp.read_resource(f"pyxel://examples/{prefix}..%2F__init__")


@pytest.mark.parametrize("link_directory", [False, True])
def test_cube_example_loader_rejects_symlinks_outside_examples(
    tmp_path, monkeypatch, link_directory
):
    root = tmp_path / "examples"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "example.py").write_text("outside the examples directory")
    if link_directory:
        (root / "cube").symlink_to(outside, target_is_directory=True)
    else:
        (root / "cube").mkdir()
        (root / "cube/example.py").symlink_to(outside / "example.py")
    monkeypatch.setattr(example_resources, "_examples_dir", lambda: root)

    with pytest.raises(ResourceError, match="not found"):
        example_resources._load_example("example", subdir="cube")
