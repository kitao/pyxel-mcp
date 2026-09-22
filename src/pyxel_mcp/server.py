"""MCPServer registration for Pyxel observation tools."""

from __future__ import annotations

import asyncio
import base64
import sys
import tempfile
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Annotated, Any

import pydantic_core
from mcp.server.mcpserver import MCPServer
from mcp.types import (
    CallToolResult,
    ContentBlock,
    ImageContent,
    TextContent,
    ToolAnnotations,
)
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

_HOMEPAGE = "https://github.com/kitao/pyxel-mcp"
_INSTRUCTIONS_PATH = Path(__file__).parent / "instructions.md"
try:
    _INSTRUCTIONS = _INSTRUCTIONS_PATH.read_text()
except FileNotFoundError:
    _INSTRUCTIONS = "pyxel-mcp instructions are missing from this installation."

# Inline PNGs are cheap for Pyxel-sized screens, but an unbounded multi-frame
# request could still flood one tool result. Extra frames stay on disk.
MAX_INLINE_IMAGES = 12


def _package_version() -> str:
    try:
        return _pkg_version("pyxel-mcp")
    except PackageNotFoundError:
        return ""


mcp = MCPServer(
    name="pyxel",
    title="Pyxel MCP",
    instructions=_INSTRUCTIONS,
    website_url=_HOMEPAGE,
    version=_package_version(),
)
register_resources(mcp)


def _annotations(title: str, *, pure: bool) -> ToolAnnotations:
    # Every tool works on local files and local subprocesses, so none of them
    # reaches an open world of external entities.
    return ToolAnnotations(
        title=title,
        read_only_hint=pure,
        destructive_hint=False,
        idempotent_hint=pure,
        open_world_hint=False,
    )


def _json_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_none=True)
    return value


def _json_list(values: list[Any] | None) -> list[Any]:
    return [_json_value(value) for value in values or []]


def _png_block(path: str) -> ImageContent:
    data = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return ImageContent(type="image", data=data, mime_type="image/png")


def _reply(
    model: type[BaseModel], result: dict[str, Any], image_paths: Sequence[str] = ()
) -> CallToolResult:
    """Build the tool result: structured data, its JSON text, and inline PNGs.

    The harness dict is normalised through the result model so every reply
    carries the same fields whichever path produced it. Inline images follow
    the JSON so the model sees captured pixels without a second file read;
    images that could not be embedded are noted as text rather than written
    into the harness facts.
    """
    structured = model.model_validate(result).model_dump(mode="json")
    text = pydantic_core.to_json(structured).decode()
    content: list[ContentBlock] = [TextContent(type="text", text=text)]
    notes: list[str] = []
    for index, path in enumerate(image_paths):
        if index >= MAX_INLINE_IMAGES:
            extra = len(image_paths) - MAX_INLINE_IMAGES
            notes.append(
                f"{extra} inline image(s) beyond the limit of {MAX_INLINE_IMAGES} stay on disk."
            )
            break
        try:
            content.append(_png_block(path))
        except OSError as exc:
            notes.append(f"Could not embed {path}: {exc.strerror or exc}.")
    content.extend(
        TextContent(type="text", text=f"[pyxel-mcp] {note}") for note in notes
    )
    return CallToolResult(content=content, structured_content=structured)


def _inline_dir() -> Path:
    """A fresh directory for PNGs the caller asked to see but not to keep.

    It lives under the system temp directory and is left for the OS to clean,
    so the reported paths stay valid for follow-up `diff_frames` calls.
    """
    return Path(tempfile.mkdtemp(prefix="pyxel-mcp-inline-"))


def _discard_if_empty(root: Path | None) -> None:
    """Drop an inline directory that received no PNG, such as after a crash."""
    if root is not None and root.is_dir() and not any(root.iterdir()):
        root.rmdir()


def _assign_inline_outputs(snapshots: list[dict[str, Any]]) -> Path | None:
    """Give path-less inline screen_image requests one file each in a new directory."""
    root: Path | None = None
    for index, snap in enumerate(snapshots):
        if snap.get("kind") != "screen_image" or not snap.get("inline"):
            continue
        if "output" in snap or "output_pattern" in snap:
            continue
        root = root or _inline_dir()
        snap["output"] = str(root / f"{index}-frame-{snap['frame']}.png")
    return root


def _inline_render_path(
    inline: bool, render_path: str | None, stem: str
) -> tuple[Path | None, str | None]:
    """Pick a temp destination for an inline render when the caller gave none."""
    if not inline or render_path is not None:
        return None, render_path
    root = _inline_dir()
    return root, str(root / f"{stem}.png")


def _inline_snapshot_paths(result: dict[str, Any]) -> list[str]:
    return [
        snapshot["path"]
        for snapshot in result.get("snapshots", [])
        if snapshot.get("kind") == "screen_image" and snapshot.get("inline")
    ]


def _rendered_path(result: dict[str, Any], inline: bool) -> list[str]:
    rendered = result.get("rendered")
    return [rendered] if inline and isinstance(rendered, str) and rendered else []


@mcp.tool(
    description=(
        "Run a Pyxel script headlessly for a frame budget or until a condition "
        "holds, with scheduled input and state, screen, or video capture. "
        "screen_image snapshots with inline=true also return the PNG as image "
        "content, and a single inline frame may omit its output path."
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
) -> Annotated[CallToolResult, RunResult]:
    """Drive a trusted local script through deterministic headless frames."""
    snapshot_payload = _json_list(snapshots)
    inline_root = _assign_inline_outputs(snapshot_payload)
    payload = {
        "script": script,
        "frames": frames,
        "inputs": _json_list(inputs),
        "snapshots": snapshot_payload,
        "random_seed": random_seed,
        "timeout": timeout,
        "stall_window_frames": stall_window_frames,
        "until": until,
    }
    try:
        result = dispatch("run", payload, timeout=timeout + 5)
    finally:
        _discard_if_empty(inline_root)
    return _reply(RunResult, result, _inline_snapshot_paths(result))


@mcp.tool(
    description="Check Python syntax and report recognizable Pyxel code patterns.",
    annotations=_annotations("Validate Pyxel script", pure=True),
    structured_output=True,
)
def validate(script: NonEmptyStr) -> Annotated[CallToolResult, ValidateResult]:
    """Read a script without executing it."""
    return _reply(ValidateResult, dispatch("validate", {"script": script}))


@mcp.tool(
    description="Report installed versions, paths, examples, and Pyxel resource URIs.",
    annotations=_annotations("Pyxel environment info", pure=True),
    structured_output=True,
)
def pyxel_info() -> Annotated[CallToolResult, PyxelInfoResult]:
    return _reply(PyxelInfoResult, dispatch("pyxel_info", {}))


@mcp.tool(
    description="Read the active Pyxel palette and the palette indices used by image banks.",
    annotations=_annotations("Read Pyxel palette", pure=False),
    structured_output=True,
)
def read_palette(script: NonEmptyStr) -> Annotated[CallToolResult, PaletteResult]:
    return _reply(PaletteResult, dispatch("read_palette", {"script": script}))


@mcp.tool(
    description=(
        "Read palette-index pixels from a Pyxel image-bank region and optionally "
        "render it to PNG; inline=true returns the render as image content and "
        "makes render_path optional."
    ),
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
    inline: bool = False,
) -> Annotated[CallToolResult, ImageResult]:
    inline_root, render_path = _inline_render_path(
        inline, render_path, f"image-{image}"
    )
    payload = {
        "script": script,
        "image": image,
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "render_path": render_path,
    }
    try:
        result = dispatch("read_image", payload)
    finally:
        _discard_if_empty(inline_root)
    return _reply(ImageResult, result, _rendered_path(result, inline))


@mcp.tool(
    description=(
        "Read Pyxel tile coordinates, usage, bounds, source bank, and optional "
        "rendered output; inline=true returns the render as image content and "
        "makes render_path optional."
    ),
    annotations=_annotations("Read tilemap", pure=False),
    structured_output=True,
)
def read_tilemap(
    script: NonEmptyStr,
    tilemap: NonNegativeInt,
    render_path: NonEmptyStr | None = None,
    inline: bool = False,
) -> Annotated[CallToolResult, TilemapResult]:
    inline_root, render_path = _inline_render_path(
        inline, render_path, f"tilemap-{tilemap}"
    )
    payload = {"script": script, "tilemap": tilemap, "render_path": render_path}
    try:
        result = dispatch("read_tilemap", payload)
    finally:
        _discard_if_empty(inline_root)
    return _reply(TilemapResult, result, _rendered_path(result, inline))


@mcp.tool(
    description=(
        "Render one Pyxel sound or music slot to WAV and return measurable audio data. "
        "Notes describe tracker fields, not an MML or PCM transcription."
    ),
    annotations=_annotations("Render audio to WAV", pure=False),
    structured_output=True,
)
def read_audio(
    script: NonEmptyStr,
    target: AudioTarget,
    output_path: NonEmptyStr,
) -> Annotated[CallToolResult, AudioResult]:
    payload = {
        "script": script,
        "target": _json_value(target),
        "output_path": output_path,
    }
    return _reply(AudioResult, dispatch("read_audio", payload))


@mcp.tool(
    description="Compare two PNG frames pixel by pixel and return their changed region and ratio.",
    annotations=_annotations("Diff two frames", pure=True),
    structured_output=True,
)
def diff_frames(
    frame_a: NonEmptyStr, frame_b: NonEmptyStr
) -> Annotated[CallToolResult, DiffFramesResult]:
    payload = {"frame_a": frame_a, "frame_b": frame_b}
    return _reply(DiffFramesResult, dispatch("diff_frames", payload))


def _log_startup() -> None:
    try:
        tool_count = len(asyncio.run(mcp.list_tools()))
    except Exception:
        tool_count = 0
    sys.stderr.write(f"[pyxel-mcp] starting - {tool_count} tools\n")


def main() -> None:
    _log_startup()
    mcp.run()


if __name__ == "__main__":
    main()
