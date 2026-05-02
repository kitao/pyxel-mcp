"""FastMCP server (spec §11.2)."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from pyxel_mcp._resources import register_resources


# Read instructions if present; placeholder if not yet rewritten (Task 9.2 will).
_INSTRUCTIONS_PATH = Path(__file__).parent / "instructions.md"
try:
    _INSTRUCTIONS = _INSTRUCTIONS_PATH.read_text()
except FileNotFoundError:
    _INSTRUCTIONS = "pyxel-mcp 0.9.3 — instructions pending."

mcp = FastMCP(name="pyxel", instructions=_INSTRUCTIONS)
register_resources(mcp)


def _dispatch(subcommand: str, payload: dict[str, Any], timeout: int = 60) -> dict[str, Any]:
    """Run the harness subprocess with payload as JSON on stdin."""
    cmd = [sys.executable, "-m", "pyxel_mcp._harnesses.main", subcommand]
    try:
        proc = subprocess.run(
            cmd,
            input=json.dumps(payload),
            capture_output=True, text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        if subcommand == "run":
            return {
                "snapshots": [], "assertions": [], "exit_status": "timeout",
                "frame_count": 0, "elapsed_seconds": float(timeout),
                "log": "", "seeded": False, "errors": [],
            }
        else:
            from pyxel_mcp._harnesses._common.error_capture import make_error, ErrorPhase
            return {"errors": [make_error(ErrorPhase.GAME_LOOP, f"subprocess timed out after {timeout}s")]}

    if proc.returncode != 0:
        from pyxel_mcp._harnesses._common.error_capture import make_error, ErrorPhase
        return {"errors": [make_error(ErrorPhase.SCRIPT_IMPORT, f"subprocess exited {proc.returncode}: {proc.stderr}")]}

    result = json.loads(proc.stdout) if proc.stdout.strip() else {}
    if subcommand == "run" and proc.stderr:
        result["log"] = (result.get("log", "") + proc.stderr) if result.get("log") else proc.stderr
    return result


@mcp.tool()
def run(
    script: str,
    frames: int,
    inputs: list[dict] | None = None,
    snapshots: list[dict] | None = None,
    random_seed: int | None = None,
    timeout: int = 10,
    stall_window_frames: int | None = None,
) -> dict:
    """Drive the script through `frames` headless Pyxel frames, applying
    scheduled `inputs` and collecting `snapshots`.

    Snapshot kinds (see `pyxel://run-snapshots-schema` for full grammar):
    - `{"frame": F, "kind": "screen_image", "output": "out.png", "scale": 1}`
    - `{"frame": F, "kind": "screen_grid", "bbox": [x, y, w, h]}` — input field
      `bbox` (list); output emits `region: {x, y, w, h}` (dict, consistent with
      inspect_image / inspect_tilemap / compare_frames)
    - `{"frame": F, "kind": "state", "attrs": ["player.x", "scene"]}` — dotted-path App attrs
    - `{"frame": F, "kind": "layout"}` — text/region balance metrics
    - `{"kind": "video", "start_frame": A, "end_frame": B, "fps": 30, "output": "clip.gif"}`
    Multi-frame: `{"frames": [10, 20, 30]}` or `{"frames": "10..50:5"}` plus `output_pattern`
    with the `{frame}` token for screen_image batches.

    Inputs schedule: list of `{"frame": F, "buttons": ["KEY_SPACE"], "axes": {...}, "mouse_pos": [x, y]}`.
    Held-until-next-row semantics; `"buttons": []` releases all.

    `random_seed` (non-negative int) seeds both `pyxel.rseed` and Python's stdlib
    random at the pre-loop checkpoint for deterministic replays. `timeout` is the
    wall-clock cap (seconds) on the run subprocess.

    `stall_window_frames` (opt-in; default None = disabled): when set to N, the
    harness keeps a rolling buffer of the last N captured `state.values` dicts
    and last N `screen_grid` hashes. If every entry in either buffer is
    identical for N consecutive frames despite scheduled inputs, the run
    breaks early with `exit_status="stalled"`. Requires at least one `state`
    or `screen_grid` snapshot scheduled — without one, the param is
    informational-only and a warning is logged.
    """
    payload = {
        "script": script, "frames": frames,
        "inputs": inputs or [], "snapshots": snapshots or [],
        "random_seed": random_seed,
        "timeout": timeout,
        "stall_window_frames": stall_window_frames,
    }
    return _dispatch("run", payload, timeout=timeout + 5)


@mcp.tool()
def validate(script: str) -> dict:
    """Static analysis: syntax + 10 anti-pattern detectors."""
    return _dispatch("validate", {"script": script})


@mcp.tool()
def pyxel_info() -> dict:
    """Report versions, stub paths, examples, and resource URIs."""
    return _dispatch("pyxel_info", {})


@mcp.tool()
def inspect_palette(script: str) -> dict:
    return _dispatch("inspect_palette", {"script": script})


@mcp.tool()
def inspect_image(
    script: str, image: int,
    x: int = 0, y: int = 0,
    w: int | None = None, h: int | None = None,
    render_path: str | None = None,
) -> dict:
    return _dispatch("inspect_image", {
        "script": script, "image": image,
        "x": x, "y": y, "w": w, "h": h, "render_path": render_path,
    })


@mcp.tool()
def inspect_animation(
    script: str, image: int,
    x: int, y: int, w: int, h: int,
    region_count: int,
    direction: str = "horizontal",
) -> dict:
    return _dispatch("inspect_animation", {
        "script": script, "image": image,
        "x": x, "y": y, "w": w, "h": h,
        "region_count": region_count, "direction": direction,
    })


@mcp.tool()
def inspect_tilemap(script: str, tilemap: int, render_path: str | None = None) -> dict:
    return _dispatch("inspect_tilemap", {"script": script, "tilemap": tilemap, "render_path": render_path})


@mcp.tool()
def render_audio(script: str, target: dict, output_path: str) -> dict:
    return _dispatch("render_audio", {"script": script, "target": target, "output_path": output_path})


@mcp.tool()
def compare_frames(frame_a: str, frame_b: str) -> dict:
    return _dispatch("compare_frames", {"frame_a": frame_a, "frame_b": frame_b})


# Aliases for direct test access without going through MCP machinery.
# @mcp.tool() returns the function unchanged (directly callable), so simple aliases work.
run_tool = run
validate_tool = validate
pyxel_info_tool = pyxel_info
inspect_palette_tool = inspect_palette
inspect_image_tool = inspect_image
inspect_animation_tool = inspect_animation
inspect_tilemap_tool = inspect_tilemap
render_audio_tool = render_audio
compare_frames_tool = compare_frames


def main() -> None:
    """Console-script entry point (pyproject.toml `pyxel-mcp = pyxel_mcp.server:main`)."""
    mcp.run()


if __name__ == "__main__":
    main()
