"""End-to-end tests for MCP handlers, transport, and metadata."""

import base64
import json
import subprocess
import tempfile
from pathlib import Path

from mcp.types import CallToolResult, ImageContent, TextContent

from pyxel_mcp import server
from pyxel_mcp.contracts import ImageResult, PaletteResult, RunResult
from pyxel_mcp.dispatch import dispatch
from pyxel_mcp.server import (
    mcp,
    pyxel_info,
    read_image,
    read_tilemap,
    run,
    validate,
)
from tests.conftest import IMAGES, SCRIPTS, structured


def test_validate_and_run_via_server():
    assert structured(validate(script=str(SCRIPTS / "minimal.py")))["ok"] is True
    assert (
        structured(run(script=str(SCRIPTS / "minimal.py"), frames=3))["exit_status"]
        == "ok"
    )


def test_run_timeout_keeps_run_result_shape():
    result = structured(
        run(script=str(SCRIPTS / "stalling.py"), frames=1000, timeout=2)
    )

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

    result = structured(
        run(
            script=str(SCRIPTS / "stalling.py"),
            frames=1000,
            timeout=1,
            snapshots=[
                {
                    "kind": "video",
                    "start_frame": 0,
                    "end_frame": 1000,
                    "output": str(tmp_path / "timeout.gif"),
                }
            ],
        )
    )

    assert result["exit_status"] == "timeout"
    assert list(tmp_path.iterdir()) == []


def test_dispatch_nonzero_exit_keeps_run_shape(monkeypatch):
    def _nonzero(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=["pyxel-mcp"], returncode=2, stdout="", stderr="boom"
        )

    monkeypatch.setattr(subprocess, "run", _nonzero)
    result = dispatch("run", {"script": "main.py", "frames": 1}, timeout=1)

    assert result["ok"] is False
    assert result["exit_status"] == "crashed"
    assert result["errors"][0]["phase"] == "script_import"
    assert result["snapshots"] == []


def test_dispatch_invalid_json_keeps_run_shape(monkeypatch):
    def _invalid(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=["pyxel-mcp"],
            returncode=0,
            stdout="SDL diagnostic\nnot json\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", _invalid)
    result = dispatch("run", {"script": "main.py", "frames": 1}, timeout=1)

    assert result["ok"] is False
    assert result["exit_status"] == "crashed"
    assert result["errors"][0]["phase"] == "script_import"


def test_dispatch_partial_run_fallback_is_normalized(monkeypatch):
    def _partial(*args, **kwargs):
        payload = {
            "errors": [
                {
                    "phase": "script_import",
                    "message": "unexpected handler failure",
                    "path": None,
                    "frame": None,
                    "traceback": None,
                }
            ]
        }
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

    result = structured(
        run(
            script=str(SCRIPTS / "minimal.py"),
            frames=1,
            snapshots=[
                {
                    "frame": 0,
                    "kind": "screen_image",
                    "output": str(not_a_directory / "frame.png"),
                }
            ],
        )
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
    result = structured(read_tilemap(script=str(SCRIPTS / "stalling.py"), tilemap=0))

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
        assert tool.annotations.destructive_hint is False
        # Local files and subprocesses only: no tool reaches an open world.
        assert tool.annotations.open_world_hint is False
        assert tool.output_schema
        assert {"ok", "errors"} <= tool.output_schema["properties"].keys()

    assert "assertions" not in by_name["run"].output_schema["properties"]
    assert by_name["pyxel_info"].annotations.read_only_hint is True
    assert by_name["run"].annotations.read_only_hint is False
    assert by_name["read_audio"].annotations.read_only_hint is False
    assert (
        by_name["read_image"].input_schema["properties"]["inline"]["default"] is False
    )

    expected_fields = {
        "validate": {"issues"},
        "pyxel_info": {
            "pyxel_mcp_version",
            "pyxel_version",
            "python_version",
            "stubs_path",
            "examples",
            "resources",
        },
        "read_palette": {"colors", "extended_palette", "palette_size", "used_indices"},
        "read_image": {
            "image_index",
            "bank_size",
            "region",
            "pixels",
            "color_count",
            "rendered",
        },
        "read_tilemap": {
            "tilemap_index",
            "size",
            "imgsrc",
            "tiles",
            "usage",
            "region",
            "zero_tile_used",
            "zero_tile_nonempty",
            "rendered",
        },
        "read_audio": {
            "path",
            "duration_seconds",
            "sample_rate",
            "channels",
            "peak_amplitude",
            "notes",
            "warnings",
        },
        "diff_frames": {
            "identical",
            "size_match",
            "size_a",
            "size_b",
            "changed_pixels",
            "total_pixels",
            "ratio",
            "region",
            "warnings",
        },
    }
    for name, fields in expected_fields.items():
        assert fields <= by_name[name].output_schema["properties"].keys()


def test_server_metadata_identifies_the_package():
    assert mcp.name == "pyxel"
    assert mcp.title == "Pyxel MCP"
    assert mcp.version == server._package_version()
    assert mcp.instructions and "eight tools" in mcp.instructions
    assert mcp.website_url == "https://github.com/kitao/pyxel-mcp"


async def test_structured_result_preserves_tool_fields():
    reply = await mcp.call_tool("validate", {"script": str(SCRIPTS / "minimal.py")})

    assert isinstance(reply, CallToolResult)
    assert [type(block) for block in reply.content] == [TextContent]
    result = structured(reply)
    assert json.loads(reply.content[0].text) == result
    assert result["ok"] is True
    assert result["errors"] == []
    assert "issues" in result


def test_inline_screen_image_returns_image_content(tmp_path):
    reply = run(
        script=str(SCRIPTS / "minimal.py"),
        frames=2,
        snapshots=[
            {"kind": "screen_image", "frame": 0, "output": str(tmp_path / "a.png")},
            {
                "kind": "screen_image",
                "frame": "end",
                "output": str(tmp_path / "b.png"),
                "scale": 2,
                "inline": True,
            },
        ],
    )

    assert isinstance(reply, CallToolResult)
    images = [block for block in reply.content if isinstance(block, ImageContent)]
    assert len(images) == 1
    assert images[0].mime_type == "image/png"
    assert base64.b64decode(images[0].data) == (tmp_path / "b.png").read_bytes()

    result = structured(reply)
    assert [snap["inline"] for snap in result["snapshots"]] == [False, True]
    assert result["snapshots"][1]["frame"] == 1
    assert json.loads(reply.content[0].text) == result


def _notes(reply: CallToolResult) -> list[str]:
    return [
        block.text
        for block in reply.content
        if isinstance(block, TextContent) and block.text.startswith("[pyxel-mcp]")
    ]


def test_inline_images_are_capped_per_call(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "MAX_INLINE_IMAGES", 3)
    reply = run(
        script=str(SCRIPTS / "minimal.py"),
        frames=5,
        snapshots=[
            {
                "kind": "screen_image",
                "frames": "all",
                "output_pattern": str(tmp_path / "{frame}.png"),
                "inline": True,
            }
        ],
    )

    images = [block for block in reply.content if isinstance(block, ImageContent)]
    assert len(images) == 3
    assert _notes(reply) == [
        "[pyxel-mcp] 2 inline image(s) beyond the limit of 3 stay on disk."
    ]
    assert "[pyxel-mcp]" not in structured(reply)["log"]
    assert len(list(tmp_path.glob("*.png"))) == 5


def test_unreadable_inline_image_is_reported_as_a_note():
    reply = server._reply(
        ImageResult,
        {"ok": True, "errors": [], "rendered": "/nonexistent/render.png"},
        ["/nonexistent/render.png"],
    )

    assert not any(isinstance(block, ImageContent) for block in reply.content)
    assert _notes(reply) == [
        "[pyxel-mcp] Could not embed /nonexistent/render.png: No such file or directory."
    ]


def test_inline_render_for_read_image_and_read_tilemap(tmp_path):
    image_reply = read_image(
        script=str(SCRIPTS / "palette_default.py"),
        image=0,
        w=8,
        h=8,
        render_path=str(tmp_path / "bank.png"),
        inline=True,
    )
    tilemap_reply = read_tilemap(
        script=str(SCRIPTS / "tilemap_demo.py"),
        tilemap=0,
        render_path=str(tmp_path / "map.png"),
        inline=True,
    )
    silent_reply = read_image(
        script=str(SCRIPTS / "palette_default.py"),
        image=0,
        w=8,
        h=8,
        render_path=str(tmp_path / "quiet.png"),
    )

    for reply in (image_reply, tilemap_reply):
        assert structured(reply)["ok"] is True
        assert sum(isinstance(block, ImageContent) for block in reply.content) == 1
    assert structured(silent_reply)["ok"] is True
    assert not any(isinstance(block, ImageContent) for block in silent_reply.content)


def test_inline_without_a_path_renders_into_a_temp_directory():
    image_reply = read_image(
        script=str(SCRIPTS / "palette_default.py"), image=0, w=8, h=8, inline=True
    )
    tilemap_reply = read_tilemap(
        script=str(SCRIPTS / "tilemap_demo.py"), tilemap=0, inline=True
    )

    for reply, stem in ((image_reply, "image-0"), (tilemap_reply, "tilemap-0")):
        result = structured(reply)
        assert result["ok"] is True
        rendered = Path(result["rendered"])
        assert rendered.name == f"{stem}.png"
        assert rendered.parent.name.startswith("pyxel-mcp-inline-")
        assert rendered.exists()
        assert sum(isinstance(block, ImageContent) for block in reply.content) == 1


def test_inline_directory_is_discarded_when_nothing_was_captured(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))

    reply = read_image(script=str(SCRIPTS / "crashing_init.py"), image=0, inline=True)

    assert structured(reply)["ok"] is False
    assert not any(isinstance(block, ImageContent) for block in reply.content)
    assert list(tmp_path.iterdir()) == []


def test_path_less_inline_frames_get_distinct_files_in_one_directory(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))

    reply = run(
        script=str(SCRIPTS / "minimal.py"),
        frames=3,
        snapshots=[
            {"kind": "screen_image", "frame": 0, "inline": True},
            {"kind": "screen_image", "frame": 0, "inline": True, "scale": 3},
            {"kind": "screen_image", "frame": "end", "inline": True},
        ],
    )

    result = structured(reply)
    assert result["ok"] is True
    snaps = result["snapshots"]
    paths = [Path(snap["path"]) for snap in snaps]
    assert [path.name for path in paths] == [
        "0-frame-0.png",
        "1-frame-0.png",
        "2-frame-end.png",
    ]
    assert len({path.parent for path in paths}) == 1
    assert paths[0].parent.parent == tmp_path
    assert snaps[1]["size"] == [3 * snaps[0]["size"][0], 3 * snaps[0]["size"][1]]
    assert all(path.exists() for path in paths)
    assert sum(isinstance(block, ImageContent) for block in reply.content) == 3


async def test_every_tool_round_trips_through_the_sdk(tmp_path):
    """Success and failure results of every tool pass the SDK's schema validation."""
    palette = str(SCRIPTS / "palette_default.py")
    tilemap = str(SCRIPTS / "tilemap_demo.py")
    missing = str(tmp_path / "missing.py")
    calls = [
        ("validate", {"script": str(SCRIPTS / "minimal.py")}, True),
        ("validate", {"script": missing}, False),
        ("run", {"script": str(SCRIPTS / "minimal.py"), "frames": 1}, True),
        ("run", {"script": str(SCRIPTS / "crashing_init.py"), "frames": 1}, False),
        ("pyxel_info", {}, True),
        ("read_palette", {"script": palette}, True),
        ("read_palette", {"script": str(SCRIPTS / "crashing_init.py")}, False),
        ("read_image", {"script": palette, "image": 0, "w": 8, "h": 8}, True),
        ("read_image", {"script": palette, "image": 999}, False),
        ("read_tilemap", {"script": tilemap, "tilemap": 0}, True),
        ("read_tilemap", {"script": tilemap, "tilemap": 99}, False),
        (
            "read_audio",
            {
                "script": str(SCRIPTS / "sound_demo.py"),
                "target": {"sound": 0},
                "output_path": str(tmp_path / "s.wav"),
            },
            True,
        ),
        (
            "read_audio",
            {
                "script": missing,
                "target": {"sound": 0},
                "output_path": str(tmp_path / "t.wav"),
            },
            False,
        ),
        (
            "diff_frames",
            {
                "frame_a": str(IMAGES / "reference_a.png"),
                "frame_b": str(IMAGES / "reference_b.png"),
            },
            True,
        ),
        (
            "diff_frames",
            {"frame_a": str(tmp_path / "x.png"), "frame_b": str(tmp_path / "y.png")},
            False,
        ),
    ]
    for name, arguments, expected_ok in calls:
        reply = await mcp.call_tool(name, arguments)
        assert reply.is_error is False, (name, arguments, reply.content)
        assert reply.structured_content["ok"] is expected_ok, (name, arguments)
        assert json.loads(reply.content[0].text) == reply.structured_content


def test_until_stops_on_first_matching_frame():
    result = structured(
        run(
            script=str(SCRIPTS / "stateful_app.py"),
            frames=50,
            until="counter >= 2",
        )
    )

    assert result["until_met"] is True
    assert result["frame_count"] == 2


def test_result_models_declare_public_fields():
    assert "until_met" in RunResult.model_fields
    assert set(PaletteResult.model_fields) >= {"colors", "palette_size", "used_indices"}


def test_pyxel_info_reports_successful_environment():
    result = structured(pyxel_info())

    assert result["ok"] is True
    assert result["pyxel_version"]
