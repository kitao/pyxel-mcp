"""Tools for inspecting screen state and validating scripts."""

import asyncio
import json
import os

from pyxel_mcp._common.format import (
    format_state_report,
    format_state_timeline,
)
from pyxel_mcp._common.pyxel_env import check_script
from pyxel_mcp._common.subprocess import run_harness
from pyxel_mcp._common.validate import validate_source


async def _run_screen_harness(script_path, frame_csv, timeout=10):
    """Run screen_harness and return parsed JSON + user output."""
    return await run_harness(
        "screen",
        [script_path, frame_csv],
        cwd=os.path.dirname(script_path),
        timeout=timeout,
    )


def register(mcp):
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
        script_path, err = check_script(script_path)
        if err:
            return f"Error: {err}"

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

    @mcp.tool()
    async def inspect_screen(
        script_path: str,
        frame: int = 5,
        timeout: int = 10,
    ) -> str:
        """Capture screen as a compact color index grid.

        Returns the screen contents as a 2D array of Pyxel palette indices
        (0-15 for default palette, higher with extended colors). Much smaller
        than a screenshot image and enables programmatic comparison.

        Args:
            script_path: Absolute path to the .py script to run.
            frame: Frame number to capture (default: 5).
            timeout: Maximum seconds to wait for the script (default: 10).
        """
        script_path, err = check_script(script_path)
        if err:
            return f"Error: {err}"

        frame = max(1, min(frame, 1800))
        timeout = max(1, min(timeout, 60))

        try:
            data, user_output, stderr_text = await _run_screen_harness(
                script_path, str(frame), timeout
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
        script_path, err = check_script(script_path)
        if err:
            return f"Error: {err}"

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
    async def validate_script(script_path: str) -> str:
        """Validate a Pyxel script without running it.

        Performs AST parsing and checks for common Pyxel anti-patterns.
        Much faster than run_and_capture for catching syntax errors and
        obvious mistakes before execution.

        Args:
            script_path: Absolute path to the .py script to validate.
        """
        script_path, err = check_script(script_path, need_pyxel=False)
        if err:
            return f"Error: {err}"

        try:
            with open(script_path) as f:
                source = f.read()
        except Exception as e:
            return f"Error reading file: {e}"

        return validate_source(source, os.path.basename(script_path))
