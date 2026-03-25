"""MCP server for Pyxel, a retro game engine for Python."""

import asyncio
import glob
import json
import os
import shutil
import sys
import tempfile
from importlib.util import find_spec

from mcp.server.fastmcp import FastMCP, Image

from pyxel_mcp._audio import analyze_wav
from pyxel_mcp._errors import decode_stderr, extract_stdout
from pyxel_mcp._subprocess import run_harness, HARNESS_PATHS
from pyxel_mcp._format import (
    format_sprite_report,
    format_layout_report,
    format_state_report,
    format_state_timeline,
)
from pyxel_mcp._palette import color_name, color_contrast
from pyxel_mcp._validate import validate_source

def _pyxel_dir():
    """Find installed Pyxel package directory (without importing Pyxel)."""
    try:
        spec = find_spec("pyxel")
        if spec:
            if spec.origin:
                return os.path.dirname(spec.origin)
            if spec.submodule_search_locations:
                return list(spec.submodule_search_locations)[0]
    except (ModuleNotFoundError, ValueError):
        pass
    return None


_INSTRUCTIONS_PATH = os.path.join(os.path.dirname(__file__), "instructions.md")
try:
    with open(_INSTRUCTIONS_PATH) as f:
        _INSTRUCTIONS = f.read()
except FileNotFoundError:
    raise RuntimeError(
        f"instructions.md not found at {_INSTRUCTIONS_PATH}. "
        "Package may be corrupted — reinstall pyxel-mcp."
    )

mcp = FastMCP("pyxel-mcp", instructions=_INSTRUCTIONS)


@mcp.tool()
async def run_and_capture(
    script_path: str,
    frames: int = 60,
    scale: int = 1,
    timeout: int = 10,
) -> list:
    """Run a Pyxel script and capture a screenshot after N frames.

    Args:
        script_path: Absolute path to the .py script to run.
        frames: Number of frames to render before capturing (default: 60).
        scale: Screenshot scale multiplier (default: 1).
        timeout: Maximum seconds to wait for the script (default: 10).
    """
    if not _pyxel_dir():
        return ["Error: Pyxel is not installed. Run: pip install pyxel-mcp"]

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return [f"Error: script not found: {script_path}"]

    frames = max(1, min(frames, 1800))
    scale = max(1, min(scale, 10))
    timeout = max(1, min(timeout, 60))

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        output_path = tmp.name

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, HARNESS_PATHS["run"],
            script_path, output_path, str(frames), str(scale),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(script_path),
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
            error_msg = decode_stderr(stderr) or "Unknown error"
            return [f"Capture failed (exit code {proc.returncode}): {error_msg}"]

        with open(output_path, "rb") as f:
            image_data = f.read()
        result = [Image(data=image_data, format="png")]
        info = f"Captured at frame {frames}, scale {scale}x"
        stderr_text = decode_stderr(stderr)
        if stderr_text:
            info += f"\nstderr: {stderr_text}"
        result.append(info)
        return result

    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return [f"Timeout: script did not finish within {timeout}s"]
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)


@mcp.tool()
def pyxel_info() -> str:
    """Get Pyxel installation info: package location, examples path, and API stubs path."""
    pyxel_dir = _pyxel_dir()
    if not pyxel_dir:
        return (
            "Pyxel is not installed.\n"
            "Install it with: pip install pyxel-mcp\n"
            "See https://github.com/kitao/pyxel for details."
        )
    examples = os.path.join(pyxel_dir, "examples")
    pyi = os.path.join(pyxel_dir, "__init__.pyi")
    lines = [
        f"Pyxel package: {pyxel_dir}",
        f"API type stubs: {pyi}" + (" (found)" if os.path.isfile(pyi) else " (not found)"),
        f"Examples dir: {examples}" + (" (found)" if os.path.isdir(examples) else " (not found)"),
    ]
    if os.path.isdir(examples):
        files = sorted(glob.glob(os.path.join(examples, "*.py")))
        lines.append(f"Examples: {', '.join(os.path.basename(f) for f in files)}")
    return "\n".join(lines)


@mcp.tool()
async def render_audio(
    script_path: str,
    sound_index: int = 0,
    duration_sec: float = 0,
    timeout: int = 10,
    music_index: int = -1,
) -> str:
    """Render a Pyxel sound or music to WAV and return waveform analysis.

    Runs the script to set up sounds (without starting the game loop),
    then renders the specified sound or music to WAV and analyzes the audio.
    Returns note sequence with timing, frequency, and volume data.

    Args:
        script_path: Absolute path to the .py script to run.
        sound_index: Sound slot index (default: 0). Default range 0-63,
            but lists can be extended via append(). Ignored when music_index is set.
        duration_sec: Duration in seconds. 0 = auto-detect from sound length (10s for music).
        timeout: Maximum seconds to wait for the script (default: 10).
        music_index: Music slot index. Default range 0-7, extendable.
            When set (>=0), renders the full multi-channel music mix instead of a single sound.
    """
    if not _pyxel_dir():
        return "Error: Pyxel is not installed. Run: pip install pyxel-mcp"

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return f"Error: script not found: {script_path}"

    sound_index = max(0, sound_index)
    music_index = max(-1, music_index)
    timeout = max(1, min(timeout, 60))
    if duration_sec > 0:
        duration_sec = min(duration_sec, 30.0)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        output_path = tmp.name

    try:
        harness_args = [
            script_path,
            output_path,
            str(sound_index),
            str(duration_sec) if duration_sec > 0 else "0",
        ]
        if music_index >= 0:
            harness_args.append(str(music_index))

        proc = await asyncio.create_subprocess_exec(
            sys.executable, HARNESS_PATHS["audio"], *harness_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(script_path),
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
            error_msg = decode_stderr(stderr) or "Unknown error"
            return f"Render failed (exit code {proc.returncode}): {error_msg}"

        meta = {}
        user_output = ""
        if stdout:
            try:
                json_str, user_output = extract_stdout(stdout)
                meta = json.loads(json_str) if json_str else {}
            except (json.JSONDecodeError, ValueError):
                pass

        try:
            analysis = await asyncio.to_thread(analyze_wav, output_path)
        except Exception as e:
            analysis = f"WAV analysis failed: {e}"

        if music_index >= 0:
            result = (
                f"Music {music_index} rendered"
                f" ({meta.get('duration_sec', '?')}s,"
                f" {meta.get('num_channels', '?')} channels)\n\n{analysis}"
            )
        else:
            result = (
                f"Sound {sound_index} rendered"
                f" ({meta.get('duration_sec', '?')}s,"
                f" speed={meta.get('speed', '?')})\n\n{analysis}"
            )
        if user_output:
            result = f"Script output:\n{user_output}\n\n{result}"
        stderr_text = decode_stderr(stderr)
        if stderr_text:
            result += f"\n\nstderr: {stderr_text}"
        return result

    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return f"Timeout: script did not finish within {timeout}s"
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)


# --- Sprite analysis ---


@mcp.tool()
async def inspect_sprite(
    script_path: str,
    image: int = 0,
    x: int = 0,
    y: int = 0,
    w: int = 8,
    h: int = 8,
    timeout: int = 10,
) -> str:
    """Inspect sprite pixel data from a Pyxel image bank.

    Reads pixel data, checks horizontal/vertical symmetry, and reports
    color usage. Use this to verify sprite quality and find asymmetries.

    Args:
        script_path: Absolute path to the .py script to run.
        image: Image bank index (default: 0). Default range 0-2, extendable.
        x: X position in the image bank (default: 0).
        y: Y position in the image bank (default: 0).
        w: Width of the region to inspect (default: 8).
        h: Height of the region to inspect (default: 8).
        timeout: Maximum seconds to wait for the script (default: 10).
    """
    if not _pyxel_dir():
        return "Error: Pyxel is not installed. Run: pip install pyxel-mcp"

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return f"Error: script not found: {script_path}"

    image = max(0, image)
    x = max(0, x)
    y = max(0, y)
    w = max(1, w)
    h = max(1, h)
    timeout = max(1, min(timeout, 60))

    try:
        data, user_output, stderr_text = await run_harness(
            "sprite",
            [script_path, str(image), str(x), str(y), str(w), str(h)],
            cwd=os.path.dirname(script_path),
            timeout=timeout,
        )
        report = format_sprite_report(data)

        if user_output:
            report = f"Script output:\n{user_output}\n\n{report}"
        if stderr_text:
            report += f"\n\nstderr: {stderr_text}"
        return report

    except RuntimeError as e:
        return str(e)
    except asyncio.TimeoutError:
        return f"Timeout: script did not finish within {timeout}s"
    except json.JSONDecodeError as e:
        return f"Failed to parse sprite data: {e}"


# --- Multi-frame capture ---


@mcp.tool()
async def capture_frames(
    script_path: str,
    frames: str = "1,15,30,60",
    scale: int = 1,
    timeout: int = 30,
) -> list:
    """Capture screenshots at multiple frame points for animation verification.

    Returns multiple images captured at specified frame numbers.
    Useful for verifying animations, transitions, and time-based effects.

    Args:
        script_path: Absolute path to the .py script to run.
        frames: Comma-separated frame numbers to capture (default: "1,15,30,60").
        scale: Screenshot scale multiplier (default: 1).
        timeout: Maximum seconds to wait for the script (default: 30).
    """
    if not _pyxel_dir():
        return ["Error: Pyxel is not installed. Run: pip install pyxel-mcp"]

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return [f"Error: script not found: {script_path}"]

    try:
        frame_list = [max(1, min(int(f.strip()), 1800)) for f in frames.split(",")]
    except ValueError:
        return ["Error: frames must be comma-separated integers (e.g. '1,15,30,60')"]

    frame_list = sorted(set(frame_list))
    if not frame_list:
        return ["Error: no valid frame numbers provided"]

    scale = max(1, min(scale, 10))
    timeout = max(1, min(timeout, 120))

    output_dir = tempfile.mkdtemp(prefix="pyxel_frames_")

    try:
        frame_csv = ",".join(str(f) for f in frame_list)
        proc = await asyncio.create_subprocess_exec(
            sys.executable, HARNESS_PATHS["frames"],
            script_path, output_dir, frame_csv, str(scale),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(script_path),
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        result = []
        for frame_num in frame_list:
            png_path = os.path.join(output_dir, f"frame_{frame_num:04d}.png")
            if os.path.isfile(png_path) and os.path.getsize(png_path) > 0:
                with open(png_path, "rb") as f:
                    result.append(Image(data=f.read(), format="png"))
                result.append(f"Frame {frame_num}")

        if not result:
            # Check for show-based capture
            show_path = os.path.join(output_dir, "frame_show.png")
            if os.path.isfile(show_path):
                with open(show_path, "rb") as f:
                    result.append(Image(data=f.read(), format="png"))
                result.append("Captured via pyxel.show()")

        if not result:
            error_msg = decode_stderr(stderr) or "No frames captured"
            return [f"Capture failed (exit code {proc.returncode}): {error_msg}"]

        stderr_text = decode_stderr(stderr)
        info = f"Captured {len([r for r in result if isinstance(r, Image)])} frames"
        if stderr_text:
            info += f"\nstderr: {stderr_text}"
        result.append(info)
        return result

    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return [f"Timeout: script did not finish within {timeout}s"]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


# --- Input simulation ---


@mcp.tool()
async def play_and_capture(
    script_path: str,
    inputs: str,
    frames: str = "1,30,60",
    scale: int = 1,
    timeout: int = 30,
) -> list:
    """Play a game by sending simulated input and capture screenshots.

    Simulates keyboard/mouse input at specific frames and captures screenshots
    at specified frame points. Use this to test input-dependent game logic
    (menus, movement, shooting) without manual play.

    Args:
        script_path: Absolute path to the .py script to run.
        inputs: JSON array of input events. Each event:
            {"frame": N, "keys": ["KEY_SPACE", ...], "mouse_x": X, "mouse_y": Y}
            Keys are held from their frame until a later entry changes them.
            Default state: no keys pressed, mouse at (0,0).
        frames: Comma-separated frame numbers to capture screenshots (default: "1,30,60").
        scale: Screenshot scale multiplier (default: 1).
        timeout: Maximum seconds to wait for the script (default: 30).
    """
    if not _pyxel_dir():
        return ["Error: Pyxel is not installed. Run: pip install pyxel-mcp"]

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return [f"Error: script not found: {script_path}"]

    try:
        input_data = json.loads(inputs)
        if not isinstance(input_data, list):
            return ["Error: inputs must be a JSON array"]
    except json.JSONDecodeError as e:
        return [f"Error: invalid inputs JSON: {e}"]

    try:
        frame_list = [max(1, min(int(f.strip()), 1800)) for f in frames.split(",")]
    except ValueError:
        return ["Error: frames must be comma-separated integers (e.g. '1,30,60')"]

    frame_list = sorted(set(frame_list))
    if not frame_list:
        return ["Error: no valid frame numbers provided"]

    scale = max(1, min(scale, 10))
    timeout = max(1, min(timeout, 120))

    output_dir = tempfile.mkdtemp(prefix="pyxel_input_")
    input_tmp = None

    try:
        # Write input schedule to temp file
        fd, input_tmp = tempfile.mkstemp(prefix="pyxel_input_", suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(input_data, f)

        frame_csv = ",".join(str(f) for f in frame_list)
        proc = await asyncio.create_subprocess_exec(
            sys.executable, HARNESS_PATHS["input"],
            script_path, output_dir, frame_csv, str(scale), input_tmp,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(script_path),
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        result = []
        for frame_num in frame_list:
            png_path = os.path.join(output_dir, f"frame_{frame_num:04d}.png")
            if os.path.isfile(png_path) and os.path.getsize(png_path) > 0:
                with open(png_path, "rb") as f:
                    result.append(Image(data=f.read(), format="png"))
                result.append(f"Frame {frame_num}")

        if not result:
            show_path = os.path.join(output_dir, "frame_show.png")
            if os.path.isfile(show_path):
                with open(show_path, "rb") as f:
                    result.append(Image(data=f.read(), format="png"))
                result.append("Captured via pyxel.show()")

        if not result:
            error_msg = decode_stderr(stderr) or "No frames captured"
            return [f"Capture failed (exit code {proc.returncode}): {error_msg}"]

        stderr_text = decode_stderr(stderr)
        info = f"Captured {len([r for r in result if isinstance(r, Image)])} frames"
        n_inputs = len(input_data)
        info += f" with {n_inputs} input event{'s' if n_inputs != 1 else ''}"
        if stderr_text:
            info += f"\nstderr: {stderr_text}"
        result.append(info)
        return result

    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return [f"Timeout: script did not finish within {timeout}s"]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        if input_tmp and os.path.isfile(input_tmp):
            os.unlink(input_tmp)


# --- Layout analysis ---


@mcp.tool()
async def inspect_layout(
    script_path: str,
    frames: int = 5,
    timeout: int = 10,
) -> str:
    """Analyze screen layout, text alignment, and visual balance.

    Detects text positions, checks horizontal balance, and identifies
    centering issues. Use this to verify UI layout quality.

    Args:
        script_path: Absolute path to the .py script to run.
        frames: Frame number to analyze (default: 5).
        timeout: Maximum seconds to wait for the script (default: 10).
    """
    if not _pyxel_dir():
        return "Error: Pyxel is not installed. Run: pip install pyxel-mcp"

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return f"Error: script not found: {script_path}"

    frames = max(1, min(frames, 1800))
    timeout = max(1, min(timeout, 60))

    try:
        data, user_output, stderr_text = await run_harness(
            "layout",
            [script_path, str(frames)],
            cwd=os.path.dirname(script_path),
            timeout=timeout,
        )
        report = format_layout_report(data)

        if user_output:
            report = f"Script output:\n{user_output}\n\n{report}"
        if stderr_text:
            report += f"\n\nstderr: {stderr_text}"
        return report

    except RuntimeError as e:
        return str(e)
    except asyncio.TimeoutError:
        return f"Timeout: script did not finish within {timeout}s"
    except json.JSONDecodeError as e:
        return f"Failed to parse layout data: {e}"


# --- State inspection ---


@mcp.tool()
async def inspect_state(
    script_path: str,
    frames: str = "60",
    attributes: str = "",
    timeout: int = 10,
) -> str:
    """Read game object attributes at specific frames for debugging.

    Captures the App instance (the class that calls pyxel.run()) and
    dumps its attributes as JSON. Supports single frame or comma-separated
    multi-frame timeline with automatic diff between frames.

    Args:
        script_path: Absolute path to the .py script to run.
        frames: Frame number(s) to inspect, comma-separated (default: "60").
            Use multiple frames for timeline diff: "10,30,60"
        attributes: Comma-separated attribute names to inspect (default: all).
        timeout: Maximum seconds to wait for the script (default: 10).
    """
    if not _pyxel_dir():
        return "Error: Pyxel is not installed. Run: pip install pyxel-mcp"

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return f"Error: script not found: {script_path}"

    try:
        frame_list = [max(1, min(int(f.strip()), 1800)) for f in frames.split(",")]
    except ValueError:
        return "Error: frames must be comma-separated integers"

    frame_list = sorted(set(frame_list))
    timeout = max(1, min(timeout, 60))

    frame_csv = ",".join(str(f) for f in frame_list)
    harness_args = [script_path, frame_csv]
    if attributes.strip():
        attr_list = [a.strip() for a in attributes.split(",") if a.strip()]
        harness_args.append(json.dumps(attr_list))

    try:
        data, user_output, stderr_text = await run_harness(
            "state",
            harness_args,
            cwd=os.path.dirname(script_path),
            timeout=timeout,
        )

        if isinstance(data, list):
            report = format_state_timeline(data)
        else:
            report = format_state_report(data)

        if user_output:
            report = f"Script output:\n{user_output}\n\n{report}"
        if stderr_text:
            report += f"\n\nstderr: {stderr_text}"
        return report

    except RuntimeError as e:
        return str(e)
    except asyncio.TimeoutError:
        return f"Timeout: script did not finish within {timeout}s"
    except json.JSONDecodeError as e:
        return f"Failed to parse state data: {e}"


# --- Script validation ---


@mcp.tool()
async def validate_script(script_path: str) -> str:
    """Validate a Pyxel script without running it.

    Performs AST parsing and checks for common Pyxel anti-patterns.
    Much faster than run_and_capture for catching syntax errors and
    obvious mistakes before execution.

    Args:
        script_path: Absolute path to the .py script to validate.
    """
    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return f"Error: script not found: {script_path}"

    try:
        with open(script_path) as f:
            source = f.read()
    except Exception as e:
        return f"Error reading file: {e}"

    return validate_source(source, os.path.basename(script_path))


# --- Screen analysis ---


async def _run_screen_harness(script_path, frame_csv, timeout=10):
    """Run screen_harness and return parsed JSON + user output."""
    return await run_harness(
        "screen",
        [script_path, frame_csv],
        cwd=os.path.dirname(script_path),
        timeout=timeout,
    )


@mcp.tool()
async def inspect_screen(
    script_path: str,
    frames: int = 5,
    timeout: int = 10,
) -> str:
    """Capture screen as a compact color index grid.

    Returns the screen contents as a 2D array of Pyxel palette indices
    (0-15 for default palette, higher with extended colors). Much smaller
    than a screenshot image and enables programmatic comparison.

    Args:
        script_path: Absolute path to the .py script to run.
        frames: Frame number to capture (default: 5).
        timeout: Maximum seconds to wait for the script (default: 10).
    """
    if not _pyxel_dir():
        return "Error: Pyxel is not installed. Run: pip install pyxel-mcp"

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return f"Error: script not found: {script_path}"

    frames = max(1, min(frames, 1800))
    timeout = max(1, min(timeout, 60))

    try:
        data, user_output, stderr_text = await _run_screen_harness(
            script_path, str(frames), timeout
        )
    except (RuntimeError, json.JSONDecodeError) as e:
        return str(e)
    except asyncio.TimeoutError:
        return f"Timeout: script did not finish within {timeout}s"

    snap = data[0] if isinstance(data, list) else data
    w, h = snap["width"], snap["height"]
    grid = snap["grid"]

    lines = [f"Screen {w}x{h} at frame {snap['frame']}"]
    lines.append("")
    has_extended = any(c > 15 for row in grid for c in row)
    for row in grid:
        if has_extended:
            lines.append(" ".join(f"{c:02x}" for c in row))
        else:
            lines.append("".join(f"{c:x}" for c in row))

    result = "\n".join(lines)
    if user_output:
        result = f"Script output:\n{user_output}\n\n{result}"
    if stderr_text:
        result += f"\n\nstderr: {stderr_text}"
    return result


@mcp.tool()
async def compare_frames(
    script_path: str,
    frame_a: int = 1,
    frame_b: int = 30,
    timeout: int = 15,
) -> str:
    """Compare screenshots at two frames and report pixel differences.

    Captures the screen as color grids at two frames and computes a diff.
    Returns changed pixel count, percentage, and which screen regions changed.
    Use this for visual regression testing.

    Args:
        script_path: Absolute path to the .py script to run.
        frame_a: First frame number (default: 1).
        frame_b: Second frame number (default: 30).
        timeout: Maximum seconds to wait for the script (default: 15).
    """
    if not _pyxel_dir():
        return "Error: Pyxel is not installed. Run: pip install pyxel-mcp"

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return f"Error: script not found: {script_path}"

    frame_a = max(1, min(frame_a, 1800))
    frame_b = max(1, min(frame_b, 1800))
    if frame_a == frame_b:
        return "Error: frame_a and frame_b must be different"
    timeout = max(1, min(timeout, 60))

    frame_csv = f"{frame_a},{frame_b}"

    try:
        data, user_output, stderr_text = await _run_screen_harness(
            script_path, frame_csv, timeout
        )
    except (RuntimeError, json.JSONDecodeError) as e:
        return str(e)
    except asyncio.TimeoutError:
        return f"Timeout: script did not finish within {timeout}s"

    if len(data) < 2:
        return "Error: could not capture both frames"

    snap_a, snap_b = data[0], data[1]
    w, h = snap_a["width"], snap_a["height"]
    grid_a, grid_b = snap_a["grid"], snap_b["grid"]

    # Compute diff
    changed = 0
    total = w * h
    min_x, min_y = w, h
    max_x, max_y = -1, -1
    changed_colors = {}

    for y in range(h):
        for x in range(w):
            if grid_a[y][x] != grid_b[y][x]:
                changed += 1
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
                key = f"{grid_a[y][x]:x}->{grid_b[y][x]:x}"
                changed_colors[key] = changed_colors.get(key, 0) + 1

    pct = changed / total * 100 if total > 0 else 0
    lines = [
        f"Frame {snap_a['frame']} vs {snap_b['frame']} ({w}x{h})",
        f"Changed pixels: {changed}/{total} ({pct:.1f}%)",
    ]

    if changed == 0:
        lines.append("Frames are identical.")
    else:
        lines.append(
            f"Changed region: ({min_x},{min_y}) to ({max_x},{max_y})"
            f" = {max_x - min_x + 1}x{max_y - min_y + 1}px"
        )
        lines.append("")
        lines.append("Color transitions (top 10):")
        for trans, count in sorted(changed_colors.items(), key=lambda x: -x[1])[:10]:
            lines.append(f"  {trans}: {count}px")

    result = "\n".join(lines)
    if user_output:
        result = f"Script output:\n{user_output}\n\n{result}"
    if stderr_text:
        result += f"\n\nstderr: {stderr_text}"
    return result


@mcp.tool()
async def inspect_palette(
    script_path: str,
    frames: int = 5,
    timeout: int = 10,
) -> str:
    """Analyze color usage and contrast in a Pyxel screenshot.

    Captures the screen and reports which colors are used, their
    distribution, background color, and potential contrast issues.
    Supports both default 16-color and extended palettes.

    Args:
        script_path: Absolute path to the .py script to run.
        frames: Frame number to analyze (default: 5).
        timeout: Maximum seconds to wait for the script (default: 10).
    """
    if not _pyxel_dir():
        return "Error: Pyxel is not installed. Run: pip install pyxel-mcp"

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return f"Error: script not found: {script_path}"

    frames = max(1, min(frames, 1800))
    timeout = max(1, min(timeout, 60))

    try:
        data, user_output, stderr_text = await _run_screen_harness(
            script_path, str(frames), timeout
        )
    except (RuntimeError, json.JSONDecodeError) as e:
        return str(e)
    except asyncio.TimeoutError:
        return f"Timeout: script did not finish within {timeout}s"

    snap = data[0] if isinstance(data, list) else data
    w, h = snap["width"], snap["height"]
    grid = snap["grid"]
    total = w * h

    # Count colors
    counts = {}
    for row in grid:
        for c in row:
            counts[c] = counts.get(c, 0) + 1

    # Detect background (most common color)
    bg_color = max(counts, key=counts.get)
    bg_name = color_name(bg_color)
    fg_colors = {c for c in counts if c != bg_color}

    lines = [
        f"Palette analysis at frame {snap['frame']} ({w}x{h})",
        f"Background: {bg_color:x} ({bg_name}) — {counts[bg_color]}/{total} pixels"
        f" ({counts[bg_color] / total * 100:.0f}%)",
        f"Colors used: {len(counts)}",
        "",
        "Color distribution:",
    ]

    for c in sorted(counts, key=counts.get, reverse=True):
        name = color_name(c)
        pct = counts[c] / total * 100
        bar = "#" * max(1, int(pct / 2))
        lines.append(f"  {c:x} ({name:10s}): {counts[c]:6d}px ({pct:5.1f}%) {bar}")

    # Contrast warnings
    warnings = []
    for c in fg_colors:
        ratio = color_contrast(c, bg_color)
        if ratio < 1.5:
            name = color_name(c)
            warnings.append(
                f"  Low contrast: {c:x}({name}) on {bg_color:x}({bg_name})"
                f" — ratio {ratio:.1f}:1"
            )

    unused = [c for c in range(16) if c not in counts]
    if unused:
        lines.append(f"\nUnused colors: {', '.join(f'{c:x}' for c in unused)}")

    if warnings:
        lines.append("\nContrast warnings:")
        lines.extend(warnings)

    result = "\n".join(lines)
    if user_output:
        result = f"Script output:\n{user_output}\n\n{result}"
    if stderr_text:
        result += f"\n\nstderr: {stderr_text}"
    return result


# --- Tilemap inspection ---


@mcp.tool()
async def inspect_tilemap(
    script_path: str,
    tilemap: int = 0,
    frames: int = 1,
    timeout: int = 10,
) -> str:
    """Inspect tilemap content, tile usage, and layout.

    Reads tilemap data and reports tile grid, usage statistics,
    bounding box of non-empty tiles, and imgsrc setting.

    Args:
        script_path: Absolute path to the .py script to run.
        tilemap: Tilemap index (default: 0). Default range 0-7, extendable.
        frames: Frame at which to read tilemap (default: 1).
        timeout: Maximum seconds to wait for the script (default: 10).
    """
    if not _pyxel_dir():
        return "Error: Pyxel is not installed. Run: pip install pyxel-mcp"

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return f"Error: script not found: {script_path}"

    tilemap = max(0, tilemap)
    frames = max(1, min(frames, 1800))
    timeout = max(1, min(timeout, 60))

    try:
        data, user_output, stderr_text = await run_harness(
            "tilemap",
            [script_path, str(tilemap), str(frames)],
            cwd=os.path.dirname(script_path),
            timeout=timeout,
        )

        lines = [
            f"Tilemap {data['tilemap_index']} ({data['width']}x{data['height']} tiles)",
            f"Image source: {data['imgsrc']}" if not isinstance(data['imgsrc'], int) else f"Image source: bank {data['imgsrc']}",
            f"Non-zero tiles: {data['non_zero_tiles']}/{data['total_scanned']}"
            f" ({data['unique_tiles']} unique)",
        ]

        bbox = data.get("bbox")
        if bbox:
            lines.append(
                f"Content bounds: ({bbox['x']},{bbox['y']})"
                f" {bbox['w']}x{bbox['h']} tiles"
            )
            lines.append("")
            lines.append("Tile grid (within bounds):")
            for row in data["tiles"]:
                cells = []
                for tile in row:
                    if tile == [0, 0]:
                        cells.append("  . ")
                    else:
                        cells.append(f"{tile[0]:2d},{tile[1]:<1d}")
                lines.append("  " + " ".join(cells))
        else:
            lines.append("Tilemap is empty (all tiles are (0,0)).")

        lines.append("")
        lines.append("Tile usage (top entries):")
        for key, count in list(data["tile_usage"].items())[:15]:
            lines.append(f"  ({key}): {count} tiles")

        result = "\n".join(lines)
        if user_output:
            result = f"Script output:\n{user_output}\n\n{result}"
        if stderr_text:
            result += f"\n\nstderr: {stderr_text}"
        return result

    except RuntimeError as e:
        return str(e)
    except asyncio.TimeoutError:
        return f"Timeout: script did not finish within {timeout}s"
    except json.JSONDecodeError as e:
        return f"Failed to parse tilemap data: {e}"


# --- Image bank visualization ---


@mcp.tool()
async def inspect_bank(
    script_path: str,
    bank: int = 0,
    scale: int = 1,
    timeout: int = 10,
) -> list:
    """Visualize a Pyxel image bank as a single screenshot.

    Renders up to 256x256 pixels of an image bank, showing sprites and
    tiles at once. Useful for verifying sprite sheet organization and
    finding available space. Custom images larger than 256x256 are cropped.

    Args:
        script_path: Absolute path to the .py script to run.
        bank: Image bank index (default: 0). Default range 0-2, extendable.
        scale: Screenshot scale multiplier (default: 1).
        timeout: Maximum seconds to wait for the script (default: 10).
    """
    if not _pyxel_dir():
        return ["Error: Pyxel is not installed. Run: pip install pyxel-mcp"]

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return [f"Error: script not found: {script_path}"]

    bank = max(0, bank)
    scale = max(1, min(scale, 4))
    timeout = max(1, min(timeout, 60))

    output_dir = tempfile.mkdtemp(prefix="pyxel_bank_")
    output_path = os.path.join(output_dir, "bank.png")

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, HARNESS_PATHS["bank"],
            script_path, output_path, str(bank), str(scale),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(script_path),
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        result = []
        if os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
            with open(output_path, "rb") as f:
                result.append(Image(data=f.read(), format="png"))
            result.append(f"Image bank {bank} (up to 256x256 pixels)")
        else:
            error_msg = decode_stderr(stderr) or "No output captured"
            return [f"Bank capture failed (exit code {proc.returncode}): {error_msg}"]

        stderr_text = decode_stderr(stderr)
        if stderr_text:
            result.append(f"stderr: {stderr_text}")
        return result

    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return [f"Timeout: script did not finish within {timeout}s"]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
