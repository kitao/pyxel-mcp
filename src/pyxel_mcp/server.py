"""FastMCP registration for Pyxel observation tools."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel

from pyxel_mcp._resources import register_resources
from pyxel_mcp.contracts import (
    AudioResult,
    AudioTarget,
    DiffFramesResult,
    ImageResult,
    InputEvent,
    NonEmptyStr,
    NonNegativeInt,
    PaletteResult,
    PositiveInt,
    PyxelInfoResult,
    RunResult,
    SnapshotRequest,
    TilemapResult,
    ValidateResult,
)
from pyxel_mcp.dispatch import dispatch


_INSTRUCTIONS_PATH = Path(__file__).parent / "instructions.md"
try:
    _INSTRUCTIONS = _INSTRUCTIONS_PATH.read_text()
except FileNotFoundError:
    _INSTRUCTIONS = "pyxel-mcp instructions are missing from this installation."

mcp = FastMCP(name="pyxel", instructions=_INSTRUCTIONS)
register_resources(mcp)


def _annotations(title: str, *, pure: bool) -> ToolAnnotations:
    return ToolAnnotations(
        title=title,
        readOnlyHint=pure,
        destructiveHint=False,
        idempotentHint=pure,
        openWorldHint=not pure,
    )


def _json_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_none=True)
    return value


def _json_list(values: list[Any] | None) -> list[Any]:
    return [_json_value(value) for value in values or []]


@mcp.tool(
    description=(
        "Run a Pyxel script headlessly for a frame budget or until a condition "
        "holds, with scheduled input and state, screen, or video capture."
    ),
    annotations=_annotations("Run Pyxel script headlessly", pure=False),
    structured_output=True,
)
def run(
    script: NonEmptyStr,
    frames: PositiveInt,
    inputs: list[InputEvent] | None = None,
    snapshots: list[SnapshotRequest] | None = None,
    random_seed: NonNegativeInt | None = None,
    timeout: PositiveInt = 10,
    stall_window_frames: PositiveInt | None = None,
    until: NonEmptyStr | None = None,
) -> RunResult:
    """Drive a trusted local script through deterministic headless frames."""
    payload = {
        "script": script,
        "frames": frames,
        "inputs": _json_list(inputs),
        "snapshots": _json_list(snapshots),
        "random_seed": random_seed,
        "timeout": timeout,
        "stall_window_frames": stall_window_frames,
        "until": until,
    }
    return dispatch("run", payload, timeout=timeout + 5)


@mcp.tool(
    description="Check Python syntax and report recognizable Pyxel code patterns.",
    annotations=_annotations("Validate Pyxel script", pure=True),
    structured_output=True,
)
def validate(script: NonEmptyStr) -> ValidateResult:
    """Read a script without executing it."""
    return dispatch("validate", {"script": script})


@mcp.tool(
    description="Report installed versions, paths, examples, and Pyxel resource URIs.",
    annotations=_annotations("Pyxel environment info", pure=True),
    structured_output=True,
)
def pyxel_info() -> PyxelInfoResult:
    return dispatch("pyxel_info", {})


@mcp.tool(
    description="Read the active Pyxel palette and the palette indices used by image banks.",
    annotations=_annotations("Read Pyxel palette", pure=False),
    structured_output=True,
)
def read_palette(script: NonEmptyStr) -> PaletteResult:
    return dispatch("read_palette", {"script": script})


@mcp.tool(
    description="Read palette-index pixels from a Pyxel image-bank region and optionally render it to PNG.",
    annotations=_annotations("Read image bank region", pure=False),
    structured_output=True,
)
def read_image(
    script: NonEmptyStr,
    image: NonNegativeInt,
    x: NonNegativeInt = 0,
    y: NonNegativeInt = 0,
    w: PositiveInt | None = None,
    h: PositiveInt | None = None,
    render_path: NonEmptyStr | None = None,
) -> ImageResult:
    return dispatch(
        "read_image",
        {
            "script": script,
            "image": image,
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "render_path": render_path,
        },
    )


@mcp.tool(
    description="Read Pyxel tile coordinates, usage, bounds, source bank, and optional rendered output.",
    annotations=_annotations("Read tilemap", pure=False),
    structured_output=True,
)
def read_tilemap(
    script: NonEmptyStr,
    tilemap: NonNegativeInt,
    render_path: NonEmptyStr | None = None,
) -> TilemapResult:
    return dispatch(
        "read_tilemap",
        {"script": script, "tilemap": tilemap, "render_path": render_path},
    )


@mcp.tool(
    description="Render one Pyxel sound or music slot to WAV and return measurable audio data.",
    annotations=_annotations("Render audio to WAV", pure=False),
    structured_output=True,
)
def read_audio(
    script: NonEmptyStr,
    target: AudioTarget,
    output_path: NonEmptyStr,
) -> AudioResult:
    return dispatch(
        "read_audio",
        {"script": script, "target": _json_value(target), "output_path": output_path},
    )


@mcp.tool(
    description="Compare two PNG frames pixel by pixel and return their changed region and ratio.",
    annotations=_annotations("Diff two frames", pure=True),
    structured_output=True,
)
def diff_frames(frame_a: NonEmptyStr, frame_b: NonEmptyStr) -> DiffFramesResult:
    return dispatch("diff_frames", {"frame_a": frame_a, "frame_b": frame_b})


def _log_startup() -> None:
    try:
        tool_count = len(mcp._tool_manager._tools)  # type: ignore[attr-defined]
    except Exception:
        tool_count = 0
    sys.stderr.write(f"[pyxel-mcp] starting - {tool_count} tools\n")


def main() -> None:
    _log_startup()
    mcp.run()


if __name__ == "__main__":
    main()
