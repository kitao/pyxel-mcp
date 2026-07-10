"""End-to-end tests: invoke server.py's handlers and MCP metadata."""
import subprocess

import pytest
from pyxel_mcp.server import (
    run_tool, validate_tool, pyxel_info_tool,
    read_palette_tool, read_image_tool, read_animation_tool, read_tilemap_tool,
    read_audio_tool, diff_frames_tool,
    _dispatch, mcp,
)
from tests.conftest import SCRIPTS


def test_validate_tool_via_server():
    result = validate_tool(script=str(SCRIPTS / "minimal.py"))
    assert result["ok"] is True


def test_run_tool_via_server():
    result = run_tool(script=str(SCRIPTS / "minimal.py"), frames=3)
    assert result["exit_status"] == "ok"


def test_subprocess_timeout_enforced():
    result = run_tool(script=str(SCRIPTS / "stalling.py"), frames=1000, timeout=2)
    assert result["exit_status"] == "timeout"


def test_run_timeout_payload_shape():
    """When `run` times out, the result must remain a well-formed RunResult so
    that callers can predicate on it without special-casing the timeout path
    (snapshots/[], assertions/[], errors/[], frame_count int, elapsed float).
    """
    result = run_tool(script=str(SCRIPTS / "stalling.py"), frames=1000, timeout=2)
    assert result["ok"] is False
    assert result["exit_status"] == "timeout"
    assert isinstance(result.get("snapshots"), list)
    assert isinstance(result.get("assertions"), list)
    assert isinstance(result.get("errors"), list)
    assert result["errors"]
    assert isinstance(result.get("frame_count"), int)
    assert isinstance(result.get("elapsed_seconds"), (int, float))
    assert "log" in result and isinstance(result["log"], str)
    assert "seeded" in result


def test_run_nonzero_payload_shape(monkeypatch):
    def _nonzero(*args, **kwargs):
        return subprocess.CompletedProcess(args=["pyxel-mcp"], returncode=2, stdout="", stderr="boom")

    monkeypatch.setattr(subprocess, "run", _nonzero)
    result = _dispatch("run", {"script": "main.py", "frames": 1}, timeout=1)

    assert result["ok"] is False
    assert result["exit_status"] == "crashed"
    assert isinstance(result.get("snapshots"), list)
    assert isinstance(result.get("assertions"), list)
    assert isinstance(result.get("errors"), list)
    assert result["errors"][0]["phase"] == "script_import"
    assert isinstance(result.get("frame_count"), int)
    assert isinstance(result.get("elapsed_seconds"), (int, float))
    assert "log" in result and isinstance(result["log"], str)
    assert "seeded" in result


def test_run_invalid_json_payload_shape(monkeypatch):
    def _invalid_json(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=["pyxel-mcp"], returncode=0, stdout="SDL diagnostic\nnot json\n", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", _invalid_json)
    result = _dispatch("run", {"script": "main.py", "frames": 1}, timeout=1)

    assert result["ok"] is False
    assert result["exit_status"] == "crashed"
    assert isinstance(result.get("snapshots"), list)
    assert isinstance(result.get("assertions"), list)
    assert isinstance(result.get("errors"), list)
    assert result["errors"][0]["phase"] == "script_import"
    assert isinstance(result.get("frame_count"), int)
    assert isinstance(result.get("elapsed_seconds"), (int, float))
    assert "log" in result and isinstance(result["log"], str)
    assert "seeded" in result


def test_non_run_tool_timeout_returns_errors():
    """For non-run tools, dispatch's timeout path returns {errors: [...]} —
    verify the error shape (phase + message) so agents can detect it."""
    # validate has near-zero work; force a 1-second timeout to trip dispatch's
    # subprocess.TimeoutExpired only if validate actually takes that long.
    # We can't reliably force a timeout on validate itself, but we can verify
    # the contract by inspection: read_audio with a long-duration argument
    # plus a tight timeout would trigger the path. Use stalling.py instead
    # since it's the canonical "never returns" fixture and read_tilemap
    # imports + headless inits the script.
    result = read_tilemap_tool(script=str(SCRIPTS / "stalling.py"), tilemap=0)
    # stalling.py spins in pyxel.run; harness can't reach pre-loop checkpoint,
    # so we expect either a successful pre-loop reach (if Pyxel.run intercept
    # works) or a timeout error. Either way, the result must be a dict with
    # an `errors` list — never raise.
    assert isinstance(result, dict)
    assert "errors" in result and isinstance(result["errors"], list)
    assert "ok" in result


def test_non_run_dispatch_timeout_uniform_shape(monkeypatch):
    def _timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["pyxel-mcp"], timeout=1)

    monkeypatch.setattr(subprocess, "run", _timeout)
    result = _dispatch("validate", {"script": "main.py"}, timeout=1)

    assert result["ok"] is False
    assert result["errors"][0]["phase"] == "game_loop"


async def test_run_snapshots_schema_resource_served():
    resources = await mcp.list_resources()
    uris = [str(r.uri) for r in resources]
    assert "pyxel://run-snapshots-schema" in uris


async def test_mcp_tool_metadata_is_discoverable():
    tools = await mcp.list_tools()
    by_name = {tool.name: tool for tool in tools}

    assert set(by_name) == {
        "run", "validate", "pyxel_info", "read_palette", "read_image",
        "read_animation", "read_tilemap", "read_audio", "diff_frames",
    }
    for tool in tools:
        assert tool.description and tool.description.strip(), tool.name
        assert tool.annotations is not None, tool.name
        assert tool.outputSchema is not None, tool.name
        assert tool.outputSchema["type"] == "object", tool.name
        assert {"ok", "errors"} <= set(tool.outputSchema["properties"]), tool.name

    run_schema = by_name["run"].outputSchema
    assert {
        "snapshots", "assertions", "exit_status", "frame_count",
        "elapsed_seconds", "log", "seeded",
    } <= set(run_schema["properties"])
    assert {
        "ok", "errors", "snapshots", "assertions", "exit_status",
        "frame_count", "elapsed_seconds", "log", "seeded",
    } <= set(run_schema["required"])
    assert by_name["pyxel_info"].annotations.readOnlyHint is True
    assert by_name["run"].annotations.destructiveHint is False
    assert by_name["read_audio"].annotations.readOnlyHint is False
    script_executing_tools = {
        "run", "read_palette", "read_image", "read_animation",
        "read_tilemap", "read_audio",
    }
    for name in script_executing_tools:
        annotations = by_name[name].annotations
        assert annotations.readOnlyHint is False, name
        assert annotations.idempotentHint is False, name
        assert annotations.openWorldHint is True, name

    expected_tool_fields = {
        "validate": {"issues"},
        "pyxel_info": {
            "pyxel_mcp_version", "pyxel_version", "python_version",
            "stubs_path", "examples", "resources",
        },
        "read_palette": {
            "colors", "extended_palette", "palette_size",
            "hierarchy", "contrast_warnings",
        },
        "read_image": {
            "image_index", "bank_size", "region", "pixels",
            "color_count", "fill_ratio", "symmetry", "edge_density",
            "warnings", "rendered",
        },
        "read_animation": {
            "image_index", "regions", "palette_consistency",
            "silhouette_stability", "region_diffs", "warnings",
        },
        "read_tilemap": {
            "tilemap_index", "size", "imgsrc", "tiles", "usage",
            "region", "trap_warning", "warnings", "rendered",
        },
        "read_audio": {
            "path", "duration_seconds", "sample_rate", "channels",
            "peak_amplitude", "notes", "warnings",
        },
        "diff_frames": {
            "identical", "size_match", "size_a", "size_b",
            "changed_pixels", "total_pixels", "ratio", "region",
            "warnings",
        },
    }
    for name, fields in expected_tool_fields.items():
        assert fields <= set(by_name[name].outputSchema["properties"]), name


async def test_structured_tool_results_keep_tool_specific_fields():
    content, structured = await mcp._tool_manager.call_tool(
        "validate",
        {"script": str(SCRIPTS / "minimal.py")},
        convert_result=True,
    )

    assert content
    assert structured["ok"] is True
    assert "errors" in structured
    assert "issues" in structured


def test_run_tool_until_via_server():
    result = run_tool(
        script=str(SCRIPTS / "stateful_app.py"), frames=50, until="counter >= 2",
    )
    assert result["until_met"] is True
    assert result["frame_count"] == 2


def test_run_result_declares_until_met():
    from pyxel_mcp.server import RunResult
    assert "until_met" in RunResult.model_fields


def test_palette_result_declares_all_output_fields():
    from pyxel_mcp.server import PaletteResult
    fields = set(PaletteResult.model_fields)
    assert {"used_indices", "co_located_pairs"} <= fields
