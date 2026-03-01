"""MCP server for Pyxel, a retro game engine for Python."""

import asyncio
import glob
import json
import math
import os
import shutil
import struct
import sys
import tempfile
import wave
from importlib.util import find_spec

from mcp.server.fastmcp import FastMCP, Image

HARNESS_PATH = os.path.join(os.path.dirname(__file__), "harness.py")
AUDIO_HARNESS_PATH = os.path.join(os.path.dirname(__file__), "audio_harness.py")
SPRITE_HARNESS_PATH = os.path.join(os.path.dirname(__file__), "sprite_harness.py")
FRAMES_HARNESS_PATH = os.path.join(os.path.dirname(__file__), "frames_harness.py")
LAYOUT_HARNESS_PATH = os.path.join(os.path.dirname(__file__), "layout_harness.py")

_MAX_STDERR = 4000


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


def _decode_stderr(stderr):
    """Decode subprocess stderr, truncating if too long."""
    if not stderr:
        return ""
    text = stderr.decode(errors="replace").strip()
    if len(text) > _MAX_STDERR:
        return text[:_MAX_STDERR] + "\n... (truncated)"
    return text


mcp = FastMCP("pyxel-mcp")


@mcp.tool()
async def run_and_capture(
    script_path: str,
    frames: int = 60,
    scale: int = 2,
    timeout: int = 10,
) -> list:
    """Run a Pyxel script and capture a screenshot after N frames.

    Args:
        script_path: Absolute path to the .py script to run.
        frames: Number of frames to render before capturing (default: 60).
        scale: Screenshot scale multiplier (default: 2).
        timeout: Maximum seconds to wait for the script (default: 10).
    """
    if not _pyxel_dir():
        return ["Error: Pyxel is not installed. Run: pip install pyxel"]

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
            sys.executable, HARNESS_PATH,
            script_path, output_path, str(frames), str(scale),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(script_path),
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
            error_msg = _decode_stderr(stderr) or "Unknown error"
            return [f"Capture failed (exit code {proc.returncode}): {error_msg}"]

        with open(output_path, "rb") as f:
            image_data = f.read()
        result = [Image(data=image_data, format="png")]
        info = f"Captured at frame {frames}, scale {scale}x"
        stderr_text = _decode_stderr(stderr)
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
            "Install it with: pip install pyxel\n"
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


# --- Audio analysis ---

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Major and minor scale templates (pitch class sets)
_SCALE_TEMPLATES = {
    "major": {0, 2, 4, 5, 7, 9, 11},
    "minor": {0, 2, 3, 5, 7, 8, 10},
    "penta": {0, 2, 4, 7, 9},
}


def _freq_to_note(freq):
    """Convert frequency (Hz) to note name like C5, A4."""
    if freq < 20:
        return "~"
    midi = 69 + 12 * math.log2(freq / 440.0)
    idx = round(midi) % 12
    octave = (round(midi) // 12) - 1
    return f"{NOTE_NAMES[idx]}{octave}"


def _freq_to_midi(freq):
    """Convert frequency to MIDI note number."""
    if freq < 20:
        return -1
    return round(69 + 12 * math.log2(freq / 440.0))


def _estimate_freq(samples, sample_rate):
    """Estimate fundamental frequency using autocorrelation."""
    n = len(samples)
    min_lag = max(1, sample_rate // 2000)  # up to 2000 Hz
    max_lag = min(sample_rate // 50, n // 2)  # down to 50 Hz
    if max_lag <= min_lag:
        return 0

    # Remove DC offset
    mean = sum(samples) / n
    centered = [s - mean for s in samples]

    # Autocorrelation: find first peak after initial decay
    energy = sum(s * s for s in centered)
    if energy == 0:
        return 0

    best_corr = -1
    best_lag = 0
    for lag in range(min_lag, max_lag):
        corr = sum(centered[i] * centered[i + lag] for i in range(n - lag))
        normalized = corr / energy
        if normalized > best_corr:
            best_corr = normalized
            best_lag = lag

    if best_lag > 0 and best_corr > 0.3:
        return sample_rate / best_lag
    return 0


def _detect_key(midi_notes):
    """Detect musical key from a list of MIDI note numbers."""
    if not midi_notes:
        return "unknown"
    # Build pitch class histogram
    pc_hist = [0] * 12
    for m in midi_notes:
        pc_hist[m % 12] += 1

    best_score = -1
    best_key = "C major"
    for root in range(12):
        for scale_name, template in _SCALE_TEMPLATES.items():
            score = sum(pc_hist[(root + pc) % 12] for pc in template)
            if score > best_score:
                best_score = score
                best_key = f"{NOTE_NAMES[root]} {scale_name}"
    return best_key


def _analyze_intervals(midi_notes):
    """Classify intervals between consecutive notes."""
    if len(midi_notes) < 2:
        return {}
    counts = {"step (1-2)": 0, "skip (3-4)": 0, "leap (5-7)": 0, "jump (8+)": 0}
    for i in range(1, len(midi_notes)):
        diff = abs(midi_notes[i] - midi_notes[i - 1])
        if diff <= 2:
            counts["step (1-2)"] += 1
        elif diff <= 4:
            counts["skip (3-4)"] += 1
        elif diff <= 7:
            counts["leap (5-7)"] += 1
        else:
            counts["jump (8+)"] += 1
    return counts


def _suggest_role(midi_notes, durations_ms):
    """Suggest channel role based on pitch range and rhythm."""
    if not midi_notes:
        return "silent"
    lo = min(midi_notes)
    hi = max(midi_notes)
    avg = sum(midi_notes) / len(midi_notes)
    unique_durs = len(set(durations_ms))

    if avg < 48:  # below C3
        return "bass"
    if avg < 60:  # C3-B3
        if unique_durs <= 2:
            return "bass"
        return "bass/accompaniment"
    if avg < 72:  # C4-B4
        if unique_durs >= 3:
            return "melody"
        return "accompaniment"
    return "melody (high)"


def _analyze_wav(wav_path):
    """Analyze WAV file and return frequency/amplitude report with musical analysis."""
    with wave.open(wav_path, "r") as wf:
        n_channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if n_frames == 0:
        return "Empty audio (0 samples)"

    samples = list(struct.unpack(f"<{n_frames * n_channels}h", raw))
    if n_channels > 1:
        samples = [
            sum(samples[i : i + n_channels]) // n_channels
            for i in range(0, len(samples), n_channels)
        ]

    duration = n_frames / sample_rate
    peak = max(abs(s) for s in samples)
    rms = math.sqrt(sum(s * s for s in samples) / len(samples))

    # Time-windowed analysis (100ms windows)
    window_size = sample_rate // 10
    segments = []
    for start in range(0, len(samples), window_size):
        w = samples[start : start + window_size]
        if len(w) < 50:
            break
        w_rms = math.sqrt(sum(s * s for s in w) / len(w))
        if w_rms < 50:
            segments.append(("~", 0, w_rms))
            continue
        freq = _estimate_freq(w, sample_rate)
        note = _freq_to_note(freq) if freq > 0 else "~"
        segments.append((note, freq, w_rms))

    # Group consecutive identical notes
    grouped = []
    for note, freq, w_rms in segments:
        if grouped and grouped[-1][0] == note:
            grouped[-1] = (
                note,
                freq,
                max(grouped[-1][2], w_rms),
                grouped[-1][3] + 100,
            )
        else:
            grouped.append((note, freq, w_rms, 100))

    lines = [
        f"Duration: {duration:.2f}s | Peak: {peak / 327.67:.0f}%"
        f" | RMS: {rms / 327.67:.0f}%",
        "",
        "Note sequence:",
    ]
    time_ms = 0
    for note, freq, w_rms, dur_ms in grouped:
        if note == "~":
            lines.append(f"  {time_ms / 1000:.1f}s [{dur_ms}ms] rest")
        else:
            lines.append(
                f"  {time_ms / 1000:.1f}s [{dur_ms}ms] {note}"
                f" (~{freq:.0f}Hz) vol={w_rms / 327.67:.0f}%"
            )
        time_ms += dur_ms

    # --- Musical analysis ---
    played = [(n, f, r, d) for n, f, r, d in grouped if n != "~"]
    if played:
        midi_notes = [_freq_to_midi(f) for _, f, _, _ in played if f > 0]
        durations = [d for _, _, _, d in played]

        if midi_notes:
            lo_note = _freq_to_note(min(f for _, f, _, _ in played if f > 0))
            hi_note = _freq_to_note(max(f for _, f, _, _ in played if f > 0))
            semitone_range = max(midi_notes) - min(midi_notes)

            lines.append("")
            lines.append("Musical analysis:")
            lines.append(
                f"  Pitch range: {lo_note} - {hi_note}"
                f" ({semitone_range} semitones)"
            )

            # Note frequency (most common)
            note_counts = {}
            for n, _, _, _ in played:
                note_counts[n] = note_counts.get(n, 0) + 1
            top_notes = sorted(note_counts.items(), key=lambda x: -x[1])[:6]
            lines.append(
                "  Top notes: "
                + " ".join(f"{n}({c}x)" for n, c in top_notes)
            )

            # Key detection
            key = _detect_key(midi_notes)
            lines.append(f"  Key estimate: {key}")

            # Interval analysis
            intervals = _analyze_intervals(midi_notes)
            if intervals:
                total = sum(intervals.values())
                parts = []
                for label, count in intervals.items():
                    if count > 0:
                        pct = count * 100 // total
                        parts.append(f"{label}:{pct}%")
                lines.append(f"  Intervals: {' '.join(parts)}")

            # Rhythm pattern
            dur_counts = {}
            for d in durations:
                dur_counts[d] = dur_counts.get(d, 0) + 1
            top_durs = sorted(dur_counts.items(), key=lambda x: -x[1])[:4]
            lines.append(
                "  Rhythm: "
                + " ".join(f"{d}ms({c}x)" for d, c in top_durs)
            )

            # Role suggestion
            role = _suggest_role(midi_notes, durations)
            lines.append(f"  Suggested role: {role}")

    return "\n".join(lines)


@mcp.tool()
async def render_audio(
    script_path: str,
    sound_index: int = 0,
    duration_sec: float = 0,
    timeout: int = 10,
) -> str:
    """Render a Pyxel sound to WAV and return waveform analysis.

    Runs the script to set up sounds (without starting the game loop),
    then renders the specified sound to WAV and analyzes the audio.
    Returns note sequence with timing, frequency, and volume data.

    Args:
        script_path: Absolute path to the .py script to run.
        sound_index: Sound slot to render, 0-63 (default: 0).
        duration_sec: Duration in seconds. 0 = auto-detect from sound length.
        timeout: Maximum seconds to wait for the script (default: 10).
    """
    if not _pyxel_dir():
        return "Error: Pyxel is not installed. Run: pip install pyxel"

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return f"Error: script not found: {script_path}"

    sound_index = max(0, min(sound_index, 63))
    timeout = max(1, min(timeout, 60))
    if duration_sec > 0:
        duration_sec = min(duration_sec, 30.0)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        output_path = tmp.name

    try:
        args = [
            sys.executable,
            AUDIO_HARNESS_PATH,
            script_path,
            output_path,
            str(sound_index),
        ]
        if duration_sec > 0:
            args.append(str(duration_sec))

        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(script_path),
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
            error_msg = _decode_stderr(stderr) or "Unknown error"
            return f"Render failed (exit code {proc.returncode}): {error_msg}"

        meta = {}
        if stdout:
            try:
                meta = json.loads(stdout.decode(errors="replace").strip())
            except json.JSONDecodeError:
                pass

        analysis = await asyncio.to_thread(_analyze_wav, output_path)
        result = (
            f"Sound {sound_index} rendered"
            f" ({meta.get('duration_sec', '?')}s,"
            f" speed={meta.get('speed', '?')})\n\n{analysis}"
        )
        stderr_text = _decode_stderr(stderr)
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

_PALETTE_NAMES = {
    0: "black", 1: "navy", 2: "purple", 3: "green",
    4: "brown", 5: "dark_blue", 6: "light_blue", 7: "white",
    8: "red", 9: "orange", 10: "yellow", 11: "lime",
    12: "cyan", 13: "gray", 14: "pink", 15: "peach",
}


def _format_sprite_report(data):
    """Format sprite inspection JSON into a readable report."""
    pixels = data["pixels"]
    region = data["region"]
    w, h = region["w"], region["h"]

    lines = [
        f"Sprite at image[{data['image']}] ({region['x']},{region['y']}) {w}x{h}",
        "",
        "Pixels (hex):",
    ]
    for row in pixels:
        hex_row = "".join(f"{c:x}" for c in row)
        lines.append(f"  {hex_row}")

    lines.append("")

    # Symmetry info
    lines.append(f"H-symmetry: {'yes' if data['symmetric_h'] else 'no'}")
    lines.append(f"V-symmetry: {'yes' if data['symmetric_v'] else 'no'}")

    # Color usage
    lines.append("")
    lines.append("Colors:")
    color_count = data["color_count"]
    for c_str, count in sorted(color_count.items(), key=lambda x: -x[1]):
        c = int(c_str) if isinstance(c_str, str) else c_str
        name = _PALETTE_NAMES.get(c, "?")
        lines.append(f"  {c:x}({name}): {count}px")

    return "\n".join(lines)


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
        image: Image bank index, 0-2 (default: 0).
        x: X position in the image bank (default: 0).
        y: Y position in the image bank (default: 0).
        w: Width of the region to inspect (default: 8).
        h: Height of the region to inspect (default: 8).
        timeout: Maximum seconds to wait for the script (default: 10).
    """
    if not _pyxel_dir():
        return "Error: Pyxel is not installed. Run: pip install pyxel"

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return f"Error: script not found: {script_path}"

    image = max(0, min(image, 2))
    x = max(0, min(x, 255))
    y = max(0, min(y, 255))
    w = max(1, min(w, 256 - x))
    h = max(1, min(h, 256 - y))
    timeout = max(1, min(timeout, 60))

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, SPRITE_HARNESS_PATH,
            script_path, str(image), str(x), str(y), str(w), str(h),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(script_path),
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        if proc.returncode != 0:
            error_msg = _decode_stderr(stderr) or "Unknown error"
            return f"Inspect failed (exit code {proc.returncode}): {error_msg}"

        data = json.loads(stdout.decode(errors="replace").strip())
        report = _format_sprite_report(data)

        stderr_text = _decode_stderr(stderr)
        if stderr_text:
            report += f"\n\nstderr: {stderr_text}"
        return report

    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return f"Timeout: script did not finish within {timeout}s"
    except json.JSONDecodeError as e:
        return f"Failed to parse sprite data: {e}"


# --- Multi-frame capture ---


@mcp.tool()
async def capture_frames(
    script_path: str,
    frames: str = "1,15,30,60",
    scale: int = 2,
    timeout: int = 30,
) -> list:
    """Capture screenshots at multiple frame points for animation verification.

    Returns multiple images captured at specified frame numbers.
    Useful for verifying animations, transitions, and time-based effects.

    Args:
        script_path: Absolute path to the .py script to run.
        frames: Comma-separated frame numbers to capture (default: "1,15,30,60").
        scale: Screenshot scale multiplier (default: 2).
        timeout: Maximum seconds to wait for the script (default: 30).
    """
    if not _pyxel_dir():
        return ["Error: Pyxel is not installed. Run: pip install pyxel"]

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
            sys.executable, FRAMES_HARNESS_PATH,
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
            error_msg = _decode_stderr(stderr) or "No frames captured"
            return [f"Capture failed (exit code {proc.returncode}): {error_msg}"]

        stderr_text = _decode_stderr(stderr)
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


# --- Layout analysis ---


def _format_layout_report(data):
    """Format layout analysis JSON into a readable report."""
    screen = data["screen"]
    bg = data["bg_color"]
    lines = [
        f"Screen: {screen['w']}x{screen['h']}  bg_color: {bg}"
        f" ({_PALETTE_NAMES.get(bg, '?')})",
    ]

    bbox = data.get("content_bbox")
    if bbox:
        cx = bbox["x"] + bbox["w"] / 2
        screen_cx = screen["w"] / 2
        offset = cx - screen_cx
        lines.append(
            f"Content bbox: ({bbox['x']},{bbox['y']})"
            f" {bbox['w']}x{bbox['h']}"
            f"  center_x={cx:.0f} (offset {offset:+.0f}px from screen center)"
        )

    fg = data["fg_pixels"]
    bal = data["h_balance"]
    lines.append(
        f"H-balance: {bal:.1%}"
        f"  (left:{fg['left']}px right:{fg['right']}px)"
    )
    if bal < 0.7:
        lines.append("  Note: significant left/right imbalance")

    text_lines = data.get("text_lines", [])
    if text_lines:
        lines.append("")
        lines.append(f"Text lines detected: {len(text_lines)}")
        screen_cx = screen["w"] / 2
        for tl in text_lines:
            color_name = _PALETTE_NAMES.get(tl["color"], "?")
            off = tl["offset_from_center"]
            align = "centered" if abs(off) <= 2 else f"offset {off:+.0f}px"
            lines.append(
                f"  y={tl['y']:3d}  x={tl['x']:3d}  w={tl['w']:3d}px"
                f"  color={tl['color']:x}({color_name})"
                f"  {align}"
            )

        # Check if texts are consistently aligned
        offsets = [tl["offset_from_center"] for tl in text_lines]
        if offsets:
            spread = max(offsets) - min(offsets)
            if spread > 20:
                lines.append(
                    f"  Note: text alignment varies by {spread:.0f}px"
                    f" across lines"
                )

    return "\n".join(lines)


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
        return "Error: Pyxel is not installed. Run: pip install pyxel"

    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return f"Error: script not found: {script_path}"

    frames = max(1, min(frames, 1800))
    timeout = max(1, min(timeout, 60))

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, LAYOUT_HARNESS_PATH,
            script_path, str(frames),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(script_path),
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        if proc.returncode != 0:
            error_msg = _decode_stderr(stderr) or "Unknown error"
            return f"Layout analysis failed (exit code {proc.returncode}): {error_msg}"

        data = json.loads(stdout.decode(errors="replace").strip())
        report = _format_layout_report(data)

        stderr_text = _decode_stderr(stderr)
        if stderr_text:
            report += f"\n\nstderr: {stderr_text}"
        return report

    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return f"Timeout: script did not finish within {timeout}s"
    except json.JSONDecodeError as e:
        return f"Failed to parse layout data: {e}"


def main():
    mcp.run()


if __name__ == "__main__":
    main()
