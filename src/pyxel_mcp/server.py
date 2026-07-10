"""FastMCP server (spec §11.2)."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

from mcp.types import ToolAnnotations
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict

from pyxel_mcp._resources import register_resources
from pyxel_mcp.observe._harnesses._common.error_capture import ErrorPhase, make_error


_INSTRUCTIONS_PATH = Path(__file__).parent / "instructions.md"
try:
    _INSTRUCTIONS = _INSTRUCTIONS_PATH.read_text()
except FileNotFoundError:
    _INSTRUCTIONS = "pyxel-mcp - instructions file missing from install."

mcp = FastMCP(name="pyxel", instructions=_INSTRUCTIONS)
register_resources(mcp)


def _annotations(title: str, *, pure: bool) -> ToolAnnotations:
    """pure=True marks tools that neither execute a user script nor write
    artifact files; clients may auto-approve and parallelize those."""
    return ToolAnnotations(
        title=title,
        readOnlyHint=pure,
        destructiveHint=False,
        idempotentHint=pure,
        openWorldHint=not pure,
    )


class ToolErrorRecord(BaseModel):
    phase: str
    message: str
    path: str | None = None
    frame: int | None = None
    traceback: str | None = None

    model_config = ConfigDict(extra="allow")


class ObservationResult(BaseModel):
    ok: bool
    errors: list[ToolErrorRecord]

    model_config = ConfigDict(extra="allow")


class RunResult(ObservationResult):
    snapshots: list[Any]
    assertions: list[Any]
    exit_status: Literal["ok", "crashed", "timeout", "stalled", "invalid"]
    frame_count: int
    elapsed_seconds: float
    log: str
    seeded: bool
    until_met: bool | None = None


class ValidateResult(ObservationResult):
    issues: list[Any] = []


class PyxelInfoResult(ObservationResult):
    pyxel_mcp_version: str | None = None
    pyxel_version: str | None = None
    python_version: str | None = None
    stubs_path: str | None = None
    examples: list[Any] = []
    resources: dict[str, str] = {}


class PaletteResult(ObservationResult):
    colors: dict[str, Any] = {}
    extended_palette: bool | None = None
    palette_size: int | None = None
    used_indices: list[Any] = []
    co_located_pairs: list[Any] = []
    hierarchy: Any = None
    contrast_warnings: list[Any] = []


class ImageResult(ObservationResult):
    image_index: int | None = None
    bank_size: list[int] | None = None
    region: dict[str, int] | None = None
    pixels: Any = None
    color_count: dict[str, Any] = {}
    fill_ratio: float | None = None
    symmetry: Any = None
    edge_density: Any = None
    warnings: list[Any] = []
    rendered: str | None = None


class AnimationResult(ObservationResult):
    image_index: int | None = None
    regions: list[Any] = []
    palette_consistency: float | None = None
    silhouette_stability: float | None = None
    region_diffs: list[Any] = []
    warnings: list[Any] = []


class TilemapResult(ObservationResult):
    tilemap_index: int | None = None
    size: list[int] | None = None
    imgsrc: int | None = None
    tiles: Any = None
    usage: dict[str, Any] = {}
    region: dict[str, int] | None = None
    trap_warning: bool | None = None
    warnings: list[Any] = []
    rendered: str | None = None


class AudioResult(ObservationResult):
    path: str | None = None
    duration_seconds: float | None = None
    sample_rate: int | None = None
    channels: int | None = None
    peak_amplitude: float | None = None
    notes: list[Any] = []
    warnings: list[Any] = []


class DiffFramesResult(ObservationResult):
    identical: bool | None = None
    size_match: bool | None = None
    size_a: list[int] | None = None
    size_b: list[int] | None = None
    changed_pixels: int | None = None
    total_pixels: int | None = None
    ratio: float | None = None
    region: dict[str, int] | None = None
    warnings: list[Any] = []


def _dispatch_error(phase, message: str) -> dict[str, Any]:
    return {"ok": False, "errors": [make_error(phase, message)]}


def _run_error_result(
    phase,
    message: str,
    *,
    exit_status: Literal["crashed", "timeout", "invalid"] = "crashed",
    elapsed_seconds: float = 0.0,
    log: str = "",
) -> dict[str, Any]:
    return {
        "ok": False,
        "snapshots": [],
        "assertions": [],
        "exit_status": exit_status,
        "frame_count": 0,
        "elapsed_seconds": elapsed_seconds,
        "log": log,
        "seeded": False,
        "until_met": None,
        "errors": [make_error(phase, message)],
    }


def _load_subprocess_json(stdout: str) -> tuple[dict[str, Any], str]:
    """Parse the harness JSON result from stdout.

    Some SDL/Pyxel builds print environment diagnostics to stdout before the
    harness writes its final one-line JSON payload. Treat preceding lines as
    diagnostics instead of failing the tool call.
    """
    text = stdout.strip()
    if not text:
        return {}, ""
    try:
        return json.loads(text), ""
    except json.JSONDecodeError:
        pass

    lines = stdout.splitlines()
    for index in range(len(lines) - 1, -1, -1):
        candidate = lines[index].strip()
        if not candidate:
            continue
        try:
            result = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        diagnostics = "\n".join(lines[:index]).strip()
        return result, diagnostics
    raise json.JSONDecodeError("no JSON payload found", stdout, 0)


def _dispatch(subcommand: str, payload: dict[str, Any], timeout: int = 60) -> dict[str, Any]:
    """Run the harness subprocess with payload as JSON on stdin."""
    cmd = [sys.executable, "-m", "pyxel_mcp.observe._harnesses.main", subcommand]
    try:
        proc = subprocess.run(
            cmd,
            input=json.dumps(payload),
            capture_output=True, text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        error = make_error(ErrorPhase.GAME_LOOP, f"subprocess timed out after {timeout}s")
        if subcommand == "run":
            return {
                "ok": False,
                "snapshots": [], "assertions": [], "exit_status": "timeout",
                "frame_count": 0, "elapsed_seconds": float(timeout),
                "log": "", "seeded": False, "until_met": None, "errors": [error],
            }
        return {"ok": False, "errors": [error]}

    if proc.returncode != 0:
        message = f"subprocess exited {proc.returncode}: {proc.stderr}"
        if subcommand == "run":
            return _run_error_result(ErrorPhase.SCRIPT_IMPORT, message, log=proc.stderr)
        return _dispatch_error(
            ErrorPhase.SCRIPT_IMPORT,
            message,
        )

    try:
        result, stdout_diagnostics = _load_subprocess_json(proc.stdout)
    except json.JSONDecodeError as e:
        message = f"subprocess returned invalid JSON: {e}: {proc.stdout[-500:]}"
        if subcommand == "run":
            return _run_error_result(ErrorPhase.SCRIPT_IMPORT, message, log=proc.stdout)
        return _dispatch_error(
            ErrorPhase.SCRIPT_IMPORT,
            message,
        )
    if not result:
        message = "subprocess returned no JSON payload"
        if subcommand == "run":
            return _run_error_result(ErrorPhase.SCRIPT_IMPORT, message, log=proc.stdout)
        return _dispatch_error(ErrorPhase.SCRIPT_IMPORT, message)
    if "ok" not in result and "errors" in result:
        result["ok"] = len(result["errors"]) == 0
    if subcommand == "run" and proc.stderr:
        result["log"] = (result.get("log", "") + proc.stderr) if result.get("log") else proc.stderr
    if subcommand == "run" and stdout_diagnostics:
        result["log"] = (
            result.get("log", "") + stdout_diagnostics
            if result.get("log")
            else stdout_diagnostics
        )
    return result


@mcp.tool(
    description="Run a Pyxel script file headlessly for N frames — or until a condition holds — scheduling inputs and capturing state, image, layout, or video snapshots.",
    annotations=_annotations("Run Pyxel script headlessly", pure=False),
    structured_output=True,
)
def run(
    script: str,
    frames: int,
    inputs: list[dict[str, Any]] | None = None,
    snapshots: list[dict[str, Any]] | None = None,
    random_seed: int | None = None,
    timeout: int = 10,
    stall_window_frames: int | None = None,
    until: str | None = None,
) -> RunResult:
    """Drive the script (a path to a Python file, not source code) through
    `frames` headless Pyxel frames, applying scheduled `inputs` and
    collecting `snapshots`.

    Snapshot kinds (see `pyxel://run-snapshots-schema` for full grammar):
    - `{"frame": F, "kind": "screen_image", "output": "/tmp/out.png", "scale": 1}`
    - `{"frame": F, "kind": "screen_grid", "bbox": [x, y, w, h]}` — input field
      `bbox` (list); output emits `region: {x, y, w, h}` (dict, consistent with
      read_image / read_tilemap / diff_frames)
    - `{"frame": F, "kind": "state", "attrs": ["player.x", "scene"]}` — dotted-path App attrs
    - `{"frame": F, "kind": "layout"}` — balance and density metrics
    - `{"kind": "video", "start_frame": A, "end_frame": B, "fps": 30, "output": "/tmp/clip.gif"}`
    Multi-frame: `{"frames": [10, 20, 30]}` or `{"frames": "10..50:5"}` plus `output_pattern`
    with the `{frame}` token for screen_image batches.

    Inputs schedule: list of `{"frame": F, "buttons": ["KEY_SPACE"], "axes": {...}, "mouse_pos": [x, y]}`.
    Held-until-next-row semantics; `"buttons": []` releases all.

    `random_seed` (non-negative int) seeds both `pyxel.rseed` and Python's stdlib
    random at the pre-loop checkpoint for deterministic replays. `timeout` is the
    wall-clock cap (seconds) on the run subprocess.

    `stall_window_frames` (opt-in; default None = disabled): when set to N, the
    harness keeps a rolling buffer of the last N captured `state.values` dicts
    and last N `screen_grid` signatures. If every entry in either buffer is
    identical for N consecutive frames despite scheduled inputs, the run
    breaks early with `exit_status="stalled"`. Requires at least one `state`
    or `screen_grid` snapshot scheduled — without one, the param is
    informational-only and a warning is logged.

    `until` (optional): a Python expression over App attributes (e.g.
    `"score >= 1"`, `"player.y > 100"`), evaluated after each frame; the run
    stops at the first frame where it holds and reports `until_met`. `frames`
    stays the hard cap. Undefined names count as not-yet-satisfied. Pair with
    `"frame": "end"` snapshots to capture the stop frame.

    `exit_status` values: `ok` (frame budget or until reached), `crashed`,
    `timeout`, `stalled`, `invalid`.
    """
    payload = {
        "script": script, "frames": frames,
        "inputs": inputs or [], "snapshots": snapshots or [],
        "random_seed": random_seed,
        "timeout": timeout,
        "stall_window_frames": stall_window_frames,
        "until": until,
    }
    return _dispatch("run", payload, timeout=timeout + 5)


@mcp.tool(
    description="Statically check a Pyxel script for syntax errors and structural Pyxel anti-patterns before running it.",
    annotations=_annotations("Validate Pyxel script", pure=True),
    structured_output=True,
)
def validate(script: str) -> ValidateResult:
    """Static analysis: syntax + 10 anti-pattern detectors.

    `script` is a path to a Python file, not source code.
    """
    return _dispatch("validate", {"script": script})


@mcp.tool(
    description="Report installed Pyxel/pyxel-mcp versions, bundled examples, stubs, and pyxel:// resource URIs.",
    annotations=_annotations("Pyxel environment info", pure=True),
    structured_output=True,
)
def pyxel_info() -> PyxelInfoResult:
    """Report versions, stub paths, examples, and resource URIs."""
    return _dispatch("pyxel_info", {})


@mcp.tool(
    description="Inspect the active Pyxel palette after script initialization, including color hierarchy and contrast warnings.",
    annotations=_annotations("Read Pyxel palette", pure=False),
    structured_output=True,
)
def read_palette(script: str) -> PaletteResult:
    """Read `pyxel.colors` and return palette usage metrics without judging quality.

    `script` is a path to a Python file, not source code.
    """
    return _dispatch("read_palette", {"script": script})


@mcp.tool(
    description="Inspect a Pyxel image-bank region, returning palette-index pixels, aggregate metrics, and optionally a rendered PNG.",
    annotations=_annotations("Read image bank region", pure=False),
    structured_output=True,
)
def read_image(
    script: str, image: int,
    x: int = 0, y: int = 0,
    w: int | None = None, h: int | None = None,
    render_path: str | None = None,
) -> ImageResult:
    """Read pixels from `pyxel.images[image]`; optional render_path writes the region PNG.

    `script` is a path to a Python file, not source code.
    """
    return _dispatch("read_image", {
        "script": script, "image": image,
        "x": x, "y": y, "w": w, "h": h, "render_path": render_path,
    })


@mcp.tool(
    description="Compare adjacent sprite-frame regions inside a Pyxel image bank for animation pixel differences.",
    annotations=_annotations("Read animation regions", pure=False),
    structured_output=True,
)
def read_animation(
    script: str, image: int,
    x: int, y: int, w: int, h: int,
    region_count: int,
    direction: Literal["horizontal", "vertical"] = "horizontal",
) -> AnimationResult:
    """Read adjacent image regions and return per-pair animation diff metrics.

    `script` is a path to a Python file, not source code.
    """
    return _dispatch("read_animation", {
        "script": script, "image": image,
        "x": x, "y": y, "w": w, "h": h,
        "region_count": region_count, "direction": direction,
    })


@mcp.tool(
    description="Inspect a Pyxel tilemap's used tiles and detect the visible (0,0) tile trap; optionally render the map.",
    annotations=_annotations("Read tilemap", pure=False),
    structured_output=True,
)
def read_tilemap(script: str, tilemap: int, render_path: str | None = None) -> TilemapResult:
    """Read `pyxel.tilemaps[tilemap]`; optional render_path writes a preview PNG.

    `script` is a path to a Python file, not source code.
    """
    return _dispatch("read_tilemap", {"script": script, "tilemap": tilemap, "render_path": render_path})


@mcp.tool(
    description="Render a Pyxel sound or music slot to WAV and return notes, peak amplitude, duration, and warnings.",
    annotations=_annotations("Render audio to WAV", pure=False),
    structured_output=True,
)
def read_audio(script: str, target: dict[str, int], output_path: str) -> AudioResult:
    """Render `target` such as `{'sound': 0}` or `{'music': 0}` to output_path.

    `script` is a path to a Python file, not source code.
    """
    return _dispatch("read_audio", {"script": script, "target": target, "output_path": output_path})


@mcp.tool(
    description="Compute a pixel-wise diff between two PNG frames, including identical flag, ratio, and changed bounding box.",
    annotations=_annotations("Diff two frames", pure=True),
    structured_output=True,
)
def diff_frames(frame_a: str, frame_b: str) -> DiffFramesResult:
    """Compare two frame PNGs without modifying either file."""
    return _dispatch("diff_frames", {"frame_a": frame_a, "frame_b": frame_b})


def _log_startup() -> None:
    """One-line stderr diagnostic so users can confirm the server loaded.

    Stderr is safe under MCP's stdio transport: stdout is reserved for
    protocol frames, stderr surfaces in host client logs.
    """
    try:
        n_tools = len(mcp._tool_manager._tools)  # type: ignore[attr-defined]
    except Exception:
        n_tools = 0
    sys.stderr.write(f"[pyxel-mcp] starting - {n_tools} tools\n")


def main() -> None:
    """Console entry point. Emit a startup diagnostic to stderr, then
    hand off to FastMCP's stdio transport loop."""
    _log_startup()
    mcp.run()


if __name__ == "__main__":
    main()
