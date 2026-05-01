"""Tools for inspecting visual assets: sprites, layouts, palettes, banks, tilemaps."""

import asyncio
import json
import os
import shutil
import tempfile

from mcp.server.fastmcp import Image

from pyxel_mcp._common.format import (
    format_animation_report,
    format_layout_report,
    format_palette_report,
    format_sprite_report,
)
from pyxel_mcp._common.pyxel_env import check_script
from pyxel_mcp._common.subprocess import run_harness, run_harness_raw
from pyxel_mcp._tools.inspect import _run_screen_harness


def register(mcp):
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
        script_path, err = check_script(script_path)
        if err:
            return f"Error: {err}"

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

    @mcp.tool()
    async def inspect_layout(
        script_path: str,
        frame: int = 5,
        timeout: int = 10,
    ) -> str:
        """Analyze screen layout, text alignment, and visual balance.

        Detects text positions, checks horizontal balance, and identifies
        centering issues. Use this to verify UI layout quality.

        Args:
            script_path: Absolute path to the .py script to run.
            frame: Frame number to analyze (default: 5).
            timeout: Maximum seconds to wait for the script (default: 10).
        """
        script_path, err = check_script(script_path)
        if err:
            return f"Error: {err}"

        frame = max(1, min(frame, 1800))
        timeout = max(1, min(timeout, 60))

        try:
            data, user_output, stderr_text = await run_harness(
                "layout",
                [script_path, str(frame)],
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

    @mcp.tool()
    async def inspect_palette(
        script_path: str,
        frame: int = 5,
        timeout: int = 10,
    ) -> str:
        """Analyze color usage and contrast in a Pyxel screenshot.

        Captures the screen and reports which colors are used, their
        distribution, background color, and potential contrast issues.
        Supports both default 16-color and extended palettes.

        Args:
            script_path: Absolute path to the .py script to run.
            frame: Frame number to analyze (default: 5).
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
        return format_palette_report(snap, user_output, stderr_text)

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
        script_path, err = check_script(script_path)
        if err:
            return [f"Error: {err}"]

        bank = max(0, bank)
        scale = max(1, min(scale, 4))
        timeout = max(1, min(timeout, 60))

        output_dir = tempfile.mkdtemp(prefix="pyxel_bank_")
        output_path = os.path.join(output_dir, "bank.png")

        try:
            _, stderr_text, returncode = await run_harness_raw(
                "bank",
                [script_path, output_path, str(bank), str(scale)],
                cwd=os.path.dirname(script_path),
                timeout=timeout,
            )

            result = []
            if os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
                with open(output_path, "rb") as f:
                    result.append(Image(data=f.read(), format="png"))
                result.append(f"Image bank {bank} (up to 256x256 pixels)")
            else:
                error_msg = stderr_text or "No output captured"
                return [f"Bank capture failed (exit code {returncode}): {error_msg}"]

            if stderr_text:
                result.append(f"stderr: {stderr_text}")
            return result

        except asyncio.TimeoutError:
            return [f"Timeout: script did not finish within {timeout}s"]
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)

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
        script_path, err = check_script(script_path)
        if err:
            return f"Error: {err}"

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

    @mcp.tool()
    async def inspect_animation(
        script_path: str,
        image: int = 0,
        x: int = 0,
        y: int = 0,
        w: int = 8,
        h: int = 8,
        frame_count: int = 2,
        timeout: int = 10,
    ) -> str:
        """Check animation frame consistency in a sprite sheet.

        Reads multiple adjacent horizontal frames and compares palette,
        silhouette size, and pixel differences between frames.

        Args:
            script_path: Absolute path to the .py script to run.
            image: Image bank index (default: 0).
            x: X position of the first frame (default: 0).
            y: Y position (default: 0).
            w: Width of each frame (default: 8).
            h: Height of each frame (default: 8).
            frame_count: Number of animation frames to check (default: 2).
            timeout: Maximum seconds to wait (default: 10).
        """
        script_path, err = check_script(script_path)
        if err:
            return f"Error: {err}"

        image = max(0, image)
        x = max(0, x)
        y = max(0, y)
        w = max(1, w)
        h = max(1, h)
        frame_count = max(2, frame_count)
        timeout = max(1, min(timeout, 60))

        try:
            data, user_output, stderr_text = await run_harness(
                "sprite",
                [script_path, str(image), str(x), str(y), str(w), str(h),
                 str(frame_count)],
                cwd=os.path.dirname(script_path),
                timeout=timeout,
            )
            report = format_animation_report(data)

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
            return f"Failed to parse animation data: {e}"
