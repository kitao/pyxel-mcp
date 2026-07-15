"""End-to-end tests for MCP handlers, transport, and metadata."""

import json
import subprocess
import tempfile

from pyxel_mcp.contracts import PaletteResult, RunResult
from pyxel_mcp.dispatch import dispatch
from pyxel_mcp.server import (
    mcp,
    pyxel_info,
    read_tilemap,
    run,
    validate,
)
from tests.conftest import SCRIPTS


def test_validate_and_run_via_server():
    assert validate(script=str(SCRIPTS / "minimal.py"))["ok"] is True
    assert run(script=str(SCRIPTS / "minimal.py"), frames=3)["exit_status"] == "ok"


def test_run_timeout_keeps_run_result_shape():
    result = run(script=str(SCRIPTS / "stalling.py"), frames=1000, timeout=2)

    assert result["ok"] is False
    assert result["exit_status"] == "timeout"
    assert result["snapshots"] == []
    assert result["errors"]
    assert isinstance(result["frame_count"], int)
    assert isinstance(result["elapsed_seconds"], float)
    assert isinstance(result["log"], str)
    assert isinstance(result["seeded"], bool)


def test_run_timeout_cleans_child_temporary_files(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))

    result = run(
        script=str(SCRIPTS / "stalling.py"),
        frames=1000,
        timeout=1,
        snapshots=[{
            "kind": "video",
            "start_frame": 0,
            "end_frame": 1000,
            "output": str(tmp_path / "timeout.gif"),
        }],
    )

    assert result["exit_status"] == "timeout"
    assert list(tmp_path.iterdir()) == []


def test_dispatch_nonzero_exit_keeps_run_shape(monkeypatch):
    def _nonzero(*args, **kwargs):
        return subprocess.CompletedProcess(args=["pyxel-mcp"], returncode=2, stdout="", stderr="boom")

    monkeypatch.setattr(subprocess, "run", _nonzero)
    result = dispatch("run", {"script": "main.py", "frames": 1}, timeout=1)

    assert result["ok"] is False
    assert result["exit_status"] == "crashed"
    assert result["errors"][0]["phase"] == "script_import"
    assert result["snapshots"] == []


def test_dispatch_invalid_json_keeps_run_shape(monkeypatch):
    def _invalid(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=["pyxel-mcp"], returncode=0, stdout="SDL diagnostic\nnot json\n", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", _invalid)
    result = dispatch("run", {"script": "main.py", "frames": 1}, timeout=1)

    assert result["ok"] is False
    assert result["exit_status"] == "crashed"
    assert result["errors"][0]["phase"] == "script_import"


def test_dispatch_partial_run_fallback_is_normalized(monkeypatch):
    def _partial(*args, **kwargs):
        payload = {"errors": [{
            "phase": "script_import",
            "message": "unexpected handler failure",
            "path": None,
            "frame": None,
            "traceback": None,
        }]}
        return subprocess.CompletedProcess(
            args=["pyxel-mcp"], returncode=0, stdout=json.dumps(payload), stderr=""
        )

    monkeypatch.setattr(subprocess, "run", _partial)
    result = dispatch("run", {"script": "main.py", "frames": 1}, timeout=1)

    RunResult.model_validate(result)
    assert result["ok"] is False
    assert result["exit_status"] == "crashed"
    assert result["errors"][0]["message"] == "unexpected handler failure"


def test_screen_snapshot_write_failure_stays_a_run_result(tmp_path):
    not_a_directory = tmp_path / "file"
    not_a_directory.write_text("occupied")

    result = run(
        script=str(SCRIPTS / "minimal.py"),
        frames=1,
        snapshots=[{
            "frame": 0,
            "kind": "screen_image",
            "output": str(not_a_directory / "frame.png"),
        }],
    )

    RunResult.model_validate(result)
    assert result["ok"] is False
    assert result["exit_status"] == "crashed"
    assert result["errors"][0]["phase"] == "artifact"


def test_dispatch_rejects_non_object_json(monkeypatch):
    def _non_object(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=["pyxel-mcp"], returncode=0, stdout="[1]", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", _non_object)
    result = dispatch("validate", {"script": "main.py"}, timeout=1)

    assert result["ok"] is False
    assert "JSON object" in result["errors"][0]["message"]


def test_dispatch_timeout_is_uniform_for_non_run_tools(monkeypatch):
    def _timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["pyxel-mcp"], timeout=1)

    monkeypatch.setattr(subprocess, "run", _timeout)
    result = dispatch("validate", {"script": "main.py"}, timeout=1)

    assert result["ok"] is False
    assert result["errors"][0]["phase"] == "game_loop"


def test_script_reader_errors_remain_structured():
    result = read_tilemap(script=str(SCRIPTS / "stalling.py"), tilemap=0)

    assert isinstance(result, dict)
    assert isinstance(result["errors"], list)
    assert "ok" in result


async def test_mcp_metadata_is_complete_and_precise():
    tools = await mcp.list_tools()
    by_name = {tool.name: tool for tool in tools}

    assert set(by_name) == {
        "run",
        "validate",
        "pyxel_info",
        "read_palette",
        "read_image",
        "read_tilemap",
        "read_audio",
        "diff_frames",
    }
    for tool in tools:
        assert tool.description and tool.description.strip()
        assert tool.annotations and tool.annotations.title
        assert tool.annotations.destructiveHint is False
        assert tool.outputSchema
        assert {"ok", "errors"} <= tool.outputSchema["properties"].keys()

    assert "assertions" not in by_name["run"].outputSchema["properties"]
    assert by_name["pyxel_info"].annotations.readOnlyHint is True
    assert by_name["run"].annotations.readOnlyHint is False
    assert by_name["read_audio"].annotations.openWorldHint is True

    expected_fields = {
        "validate": {"issues"},
        "pyxel_info": {"pyxel_mcp_version", "pyxel_version", "python_version", "stubs_path", "examples", "resources"},
        "read_palette": {"colors", "extended_palette", "palette_size", "used_indices"},
        "read_image": {"image_index", "bank_size", "region", "pixels", "color_count", "rendered"},
        "read_tilemap": {"tilemap_index", "size", "imgsrc", "tiles", "usage", "region", "zero_tile_used", "zero_tile_nonempty", "rendered"},
        "read_audio": {"path", "duration_seconds", "sample_rate", "channels", "peak_amplitude", "notes", "warnings"},
        "diff_frames": {"identical", "size_match", "size_a", "size_b", "changed_pixels", "total_pixels", "ratio", "region", "warnings"},
    }
    for name, fields in expected_fields.items():
        assert fields <= by_name[name].outputSchema["properties"].keys()


async def test_structured_result_preserves_tool_fields():
    content, structured = await mcp._tool_manager.call_tool(
        "validate",
        {"script": str(SCRIPTS / "minimal.py")},
        convert_result=True,
    )

    assert content
    assert structured["ok"] is True
    assert structured["errors"] == []
    assert "issues" in structured


def test_until_stops_on_first_matching_frame():
    result = run(
        script=str(SCRIPTS / "stateful_app.py"),
        frames=50,
        until="counter >= 2",
    )

    assert result["until_met"] is True
    assert result["frame_count"] == 2


def test_result_models_declare_public_fields():
    assert "until_met" in RunResult.model_fields
    assert set(PaletteResult.model_fields) >= {"colors", "palette_size", "used_indices"}


def test_pyxel_info_reports_successful_environment():
    result = pyxel_info()

    assert result["ok"] is True
    assert result["pyxel_version"]
