"""Tools for running Pyxel scripts and capturing output."""

import asyncio
import json
import os
import shutil
import tempfile

from mcp.server.fastmcp import Image

from pyxel_mcp._common.pyxel_env import check_script
from pyxel_mcp._common.subprocess import run_harness, run_harness_raw


async def _play_and_capture_impl(
    script_path,
    inputs,
    frames="1,30,60",
    scale=1,
    timeout=30,
) -> list:
    """Implementation for play_and_capture tool — exposed at module level for testing."""
    script_path, err = check_script(script_path)
    if err:
        return [f"Error: {err}"]

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
        _, stderr_text, returncode = await run_harness_raw(
            "input",
            [script_path, output_dir, frame_csv, str(scale), input_tmp],
            cwd=os.path.dirname(script_path),
            timeout=timeout,
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
            error_msg = stderr_text or "No frames captured"
            return [f"Capture failed (exit code {returncode}): {error_msg}"]

        info = f"Captured {len([r for r in result if isinstance(r, Image)])} frames"
        n_inputs = len(input_data)
        info += f" with {n_inputs} input event{'s' if n_inputs != 1 else ''}"
        if stderr_text:
            info += f"\nstderr: {stderr_text}"
        result.append(info)
        return result

    except asyncio.TimeoutError:
        return [f"Timeout: script did not finish within {timeout}s"]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        if input_tmp and os.path.isfile(input_tmp):
            os.unlink(input_tmp)


async def _record_gameplay_impl(
    script_path, duration=60, inputs="[]", scale=1, timeout=15,
) -> Image | str:
    """Implementation for record_gameplay tool — exposed at module level for testing."""
    abs_path, err = check_script(script_path)
    if err:
        return f"Error: {err}"

    duration = max(1, min(duration, 600))
    scale = max(1, min(scale, 4))
    timeout = max(1, min(timeout, 60))

    try:
        events = json.loads(inputs)
        if not isinstance(events, list):
            return "Error: inputs must be a JSON array"
    except json.JSONDecodeError as e:
        return f"Error: inputs is not valid JSON ({e})"

    with tempfile.TemporaryDirectory() as tmpdir:
        out_gif = os.path.join(tmpdir, "out.gif")
        input_json = os.path.join(tmpdir, "events.json")
        with open(input_json, "w") as f:
            json.dump(events, f)

        try:
            await run_harness(
                "record",
                [abs_path, out_gif, str(duration), str(scale), input_json],
                cwd=os.path.dirname(abs_path),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return f"Error: script timed out after {timeout}s"
        except RuntimeError as e:
            return f"Error: {e}"

        if not os.path.isfile(out_gif):
            return "Error: GIF not produced (script may not have rendered any frames)"

        with open(out_gif, "rb") as f:
            return Image(data=f.read(), format="gif")


def register(mcp):
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
        script_path, err = check_script(script_path)
        if err:
            return [f"Error: {err}"]

        frames = max(1, min(frames, 1800))
        scale = max(1, min(scale, 10))
        timeout = max(1, min(timeout, 60))

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            output_path = tmp.name

        try:
            _, stderr_text, returncode = await run_harness_raw(
                "run",
                [script_path, output_path, str(frames), str(scale)],
                cwd=os.path.dirname(script_path),
                timeout=timeout,
            )

            if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
                error_msg = stderr_text or "Unknown error"
                return [f"Capture failed (exit code {returncode}): {error_msg}"]

            with open(output_path, "rb") as f:
                image_data = f.read()
            result = [Image(data=image_data, format="png")]
            info = f"Captured at frame {frames}, scale {scale}x"
            if stderr_text:
                info += f"\nstderr: {stderr_text}"
            result.append(info)
            return result

        except asyncio.TimeoutError:
            return [f"Timeout: script did not finish within {timeout}s"]
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

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
        script_path, err = check_script(script_path)
        if err:
            return [f"Error: {err}"]

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
            _, stderr_text, returncode = await run_harness_raw(
                "frames",
                [script_path, output_dir, frame_csv, str(scale)],
                cwd=os.path.dirname(script_path),
                timeout=timeout,
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
                error_msg = stderr_text or "No frames captured"
                return [f"Capture failed (exit code {returncode}): {error_msg}"]

            info = f"Captured {len([r for r in result if isinstance(r, Image)])} frames"
            if stderr_text:
                info += f"\nstderr: {stderr_text}"
            result.append(info)
            return result

        except asyncio.TimeoutError:
            return [f"Timeout: script did not finish within {timeout}s"]
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)

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
        return await _play_and_capture_impl(script_path, inputs, frames, scale, timeout)

    @mcp.tool()
    async def record_gameplay(
        script_path: str,
        duration: int = 60,
        inputs: str = "[]",
        scale: int = 1,
        timeout: int = 15,
    ):
        """Record gameplay as a GIF using Pyxel's screencast.

        Returns the GIF as a single image for visual verification of
        animations, transitions, and gameplay flow over time. For
        input-driven sequences, pass a JSON string of frame events in
        `inputs` (same format as play_and_capture, with optional
        `btnv` field for analog input).

        Args:
            script_path: Absolute path to the .py script to record.
            duration: Number of frames to record (1-600, default 60).
            inputs: JSON array of frame input events (default empty).
            scale: GIF scale multiplier (1-4, default 1).
            timeout: Maximum seconds to wait for the script (default 15).
        """
        return await _record_gameplay_impl(script_path, duration, inputs, scale, timeout)
