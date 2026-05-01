"""Tools for rendering and analyzing Pyxel audio."""

import asyncio
import json
import os
import tempfile

from pyxel_mcp._common.audio import analyze_wav
from pyxel_mcp._common.errors import extract_stdout
from pyxel_mcp._common.pyxel_env import check_script
from pyxel_mcp._common.subprocess import run_harness_raw


def register(mcp):
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
        script_path, err = check_script(script_path)
        if err:
            return f"Error: {err}"

        sound_index = max(0, sound_index)
        music_index = max(-1, music_index)
        timeout = max(1, min(timeout, 60))
        if duration_sec > 0:
            duration_sec = min(duration_sec, 30.0)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            output_path = tmp.name

        harness_args = [
            script_path,
            output_path,
            str(sound_index),
            str(duration_sec) if duration_sec > 0 else "0",
        ]
        if music_index >= 0:
            harness_args.append(str(music_index))

        try:
            stdout_bytes, stderr_text, returncode = await run_harness_raw(
                "audio", harness_args,
                cwd=os.path.dirname(script_path),
                timeout=timeout,
            )

            if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
                error_msg = stderr_text or "Unknown error"
                return f"Render failed (exit code {returncode}): {error_msg}"

            meta = {}
            user_output = ""
            if stdout_bytes:
                try:
                    json_str, user_output = extract_stdout(stdout_bytes)
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
            if stderr_text:
                result += f"\n\nstderr: {stderr_text}"
            return result

        except asyncio.TimeoutError:
            return f"Timeout: script did not finish within {timeout}s"
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
