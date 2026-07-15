"""Public-contract tests for the observation-only MCP surface."""

from pathlib import Path

from pyxel_mcp.server import mcp, read_image, read_palette, read_tilemap, run

from tests.conftest import SCRIPTS


async def test_tool_surface_contains_only_observation_primitives():
    tools = await mcp.list_tools()

    assert {tool.name for tool in tools} == {
        "run",
        "validate",
        "pyxel_info",
        "read_palette",
        "read_image",
        "read_tilemap",
        "read_audio",
        "diff_frames",
    }


async def test_run_schema_describes_inputs_and_snapshot_variants():
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    schema = tools["run"].inputSchema

    inputs = schema["properties"]["inputs"]["anyOf"][0]["items"]
    snapshots = schema["properties"]["snapshots"]["anyOf"][0]["items"]

    assert inputs.get("additionalProperties") is not True
    assert "$ref" in inputs or "properties" in inputs
    assert "discriminator" in snapshots


async def test_input_schema_exposes_numeric_boundaries():
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    run_schema = tools["run"].inputSchema
    run_properties = run_schema["properties"]

    assert run_properties["frames"]["exclusiveMinimum"] == 0
    assert run_properties["random_seed"]["anyOf"][0]["minimum"] == 0
    assert run_properties["timeout"]["exclusiveMinimum"] == 0

    axes = run_schema["$defs"]["InputEvent"]["properties"]["axes"]
    axis_value = axes["anyOf"][0]["additionalProperties"]
    assert axis_value["minimum"] == -1
    assert axis_value["maximum"] == 1

    image_properties = tools["read_image"].inputSchema["properties"]
    assert image_properties["image"]["minimum"] == 0
    assert image_properties["x"]["minimum"] == 0
    assert image_properties["w"]["anyOf"][0]["exclusiveMinimum"] == 0


def test_run_rejects_removed_layout_snapshot():
    result = run(
        script=str(SCRIPTS / "minimal.py"),
        frames=2,
        snapshots=[{"kind": "layout", "frame": 1}],
    )

    assert result["ok"] is False
    assert result["exit_status"] == "invalid"


def test_run_result_has_no_console_assertion_protocol():
    result = run(script=str(SCRIPTS / "assert_passing.py"), frames=2)

    assert "assertions" not in result


def test_palette_result_contains_facts_not_quality_judgments():
    result = read_palette(script=str(SCRIPTS / "palette_default.py"))

    assert result["ok"] is True
    assert {"colors", "palette_size", "used_indices"} <= result.keys()
    assert {"co_located_pairs", "hierarchy", "contrast_warnings"}.isdisjoint(result)


def test_palette_used_indices_includes_zero_when_present():
    result = read_palette(script=str(SCRIPTS / "palette_default.py"))

    assert result["ok"] is True
    assert 0 in result["used_indices"]


def test_read_image_rejects_an_origin_outside_the_bank():
    result = read_image(
        script=str(SCRIPTS / "palette_default.py"),
        image=0,
        x=256,
        y=0,
    )

    assert result["ok"] is False
    assert result["errors"][0]["phase"] == "validation"


def test_image_result_contains_pixels_not_quality_judgments():
    result = read_image(
        script=str(SCRIPTS / "palette_default.py"),
        image=0,
        x=0,
        y=0,
        w=8,
        h=8,
    )

    assert result["ok"] is True
    assert {"pixels", "color_count", "region"} <= result.keys()
    assert {"fill_ratio", "symmetry", "edge_density", "warnings"}.isdisjoint(result)


def test_tilemap_reports_zero_tile_facts_instead_of_a_warning():
    result = read_tilemap(script=str(SCRIPTS / "tilemap_demo.py"), tilemap=0)

    assert result["ok"] is True
    assert isinstance(result["zero_tile_used"], bool)
    assert isinstance(result["zero_tile_nonempty"], bool)
    assert {"trap_warning", "warnings"}.isdisjoint(result)


async def test_resources_are_local_and_examples_use_a_template():
    resources = await mcp.list_resources()
    templates = await mcp.list_resource_templates()

    assert {str(resource.uri) for resource in resources} == {
        "pyxel://run-snapshots-schema",
        "pyxel://validation-patterns",
        "pyxel://palette/default",
    }
    assert {template.uriTemplate for template in templates} == {
        "pyxel://examples/{name}",
    }

    assert not any(
        str(resource.uri).startswith("pyxel://api-")
        or str(resource.uri).startswith("pyxel://user-guide")
        for resource in resources
    )
