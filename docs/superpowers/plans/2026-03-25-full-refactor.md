# Full Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the entire pyxel-mcp codebase — split server.py, eliminate harness duplication, boost WAV analysis performance with numpy, enhance graphics tools, and add comprehensive tests.

**Architecture:** Extract server.py (2750 lines) into focused modules (`_errors.py`, `_palette.py`, `_subprocess.py`, `_audio.py`, `_format.py`, `_validate.py`, `instructions.md`). Expand `_headless.py` to unify harness boilerplate. Use numpy FFT for ~50x WAV speedup. Add unit + integration tests.

**Tech Stack:** Python 3.10+, FastMCP, Pyxel >=2.8.8, numpy, pytest, pytest-asyncio

**Spec:** `docs/superpowers/specs/2026-03-25-full-refactor-design.md`

---

## File Map

### New files to create

| File | Responsibility |
|------|---------------|
| `src/pyxel_mcp/_errors.py` | Error hints, stderr decode, stdout JSON extraction |
| `src/pyxel_mcp/_palette.py` | Unified palette data, color name/rgb/contrast/luminance |
| `src/pyxel_mcp/_subprocess.py` | Async subprocess runner, harness path registry |
| `src/pyxel_mcp/_audio.py` | WAV analysis with numpy FFT, music theory |
| `src/pyxel_mcp/_format.py` | Report formatters for sprite/layout/state/palette |
| `src/pyxel_mcp/_validate.py` | Script validation, anti-pattern detection |
| `src/pyxel_mcp/instructions.md` | MCP instructions (extracted from server.py) |
| `tests/conftest.py` | Shared test fixtures |
| `tests/test_errors.py` | Unit tests for _errors.py |
| `tests/test_palette.py` | Unit tests for _palette.py |
| `tests/test_audio.py` | Unit tests for _audio.py |
| `tests/test_format.py` | Unit tests for _format.py |
| `tests/test_validate.py` | Unit tests for _validate.py |
| `tests/test_layout_analysis.py` | Unit tests for layout harness functions |
| `tests/test_subprocess.py` | Unit tests for _subprocess.py (mock-based) |
| `tests/test_tools.py` | Integration tests (require Pyxel) |

### Files to modify

| File | Changes |
|------|---------|
| `src/pyxel_mcp/server.py` | Strip to thin wrapper (~300 lines): imports + tool defs |
| `src/pyxel_mcp/_headless.py` | Add `init_harness`, `patch_game_loop`, `noop_game_loop` |
| `src/pyxel_mcp/harness.py` | Rewrite using `_headless` helpers (~30 lines) |
| `src/pyxel_mcp/frames_harness.py` | Rewrite using `_headless` helpers (~35 lines) |
| `src/pyxel_mcp/input_harness.py` | Rewrite using `_headless` helpers (~90 lines) |
| `src/pyxel_mcp/screen_harness.py` | Rewrite using `_headless` helpers (~35 lines) |
| `src/pyxel_mcp/state_harness.py` | Rewrite using `_headless` helpers (~75 lines) |
| `src/pyxel_mcp/layout_harness.py` | Decompose into testable functions (~200 lines) |
| `src/pyxel_mcp/tilemap_harness.py` | Rewrite using `_headless` helpers (~45 lines) |
| `src/pyxel_mcp/bank_harness.py` | Rewrite using `_headless` helpers (~30 lines) |
| `src/pyxel_mcp/sprite_harness.py` | Rewrite using `_headless` helpers (~40 lines) |
| `src/pyxel_mcp/audio_harness.py` | Rewrite using `_headless` helpers (~30 lines) |
| `pyproject.toml` | Add numpy dep, test extras, instructions.md in package data |

---

## Task 1: Project Setup — Dependencies and Test Infrastructure

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/conftest.py`

- [ ] **Step 1: Update pyproject.toml**

Add numpy dependency, test extras, and ensure instructions.md is included:

```toml
dependencies = ["mcp>=1.0.0,<2.0.0", "pyxel>=2.8.8", "numpy"]

[project.optional-dependencies]
test = ["pytest", "pytest-asyncio"]

[tool.hatch.build.targets.wheel]
packages = ["src/pyxel_mcp"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 2: Create tests/conftest.py**

```python
"""Shared test fixtures for pyxel-mcp tests."""
```

- [ ] **Step 3: Install test dependencies**

Run: `cd /Users/takashi/repos/pyxel-mcp && uv pip install -e ".[test]"`
Expected: Successfully installed with numpy, pytest, pytest-asyncio

- [ ] **Step 4: Verify pytest runs**

Run: `cd /Users/takashi/repos/pyxel-mcp && .venv/bin/python -m pytest tests/ -v --co`
Expected: "no tests ran" (empty collection, no errors)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml tests/conftest.py
git commit -m "Add numpy dependency, test infrastructure"
```

---

## Task 2: Extract `_errors.py` + Tests

**Files:**
- Create: `src/pyxel_mcp/_errors.py`
- Create: `tests/test_errors.py`
- Modify: `src/pyxel_mcp/server.py` (remove moved code, add import)

- [ ] **Step 1: Write tests for _errors.py**

```python
"""Tests for _errors module."""

from pyxel_mcp._errors import enrich_error, decode_stderr, extract_stdout

# --- enrich_error ---

def test_enrich_error_empty():
    assert enrich_error("") == ""

def test_enrich_error_no_match():
    assert enrich_error("some random error") == "some random error"

def test_enrich_error_blt_hint():
    result = enrich_error("TypeError in blt()")
    assert "blt(x, y, img, u, v, w, h" in result

def test_enrich_error_index_hint():
    result = enrich_error("IndexError: image index out of range")
    assert "Default slots" in result

def test_enrich_error_attribute_hint():
    result = enrich_error("AttributeError: module 'pyxel' has no attribute 'foo'")
    assert "Check API spelling" in result

def test_enrich_error_name_hint():
    result = enrich_error("NameError: name 'KEY_SPACE' is not defined")
    assert "pyxel.KEY_SPACE" in result

def test_enrich_error_int_callable_hint():
    result = enrich_error("TypeError: 'int' object is not callable")
    assert "mouse_x" in result

def test_enrich_error_recursion_hint():
    result = enrich_error("RecursionError: maximum recursion depth exceeded")
    assert "pyxel.run()" in result

# --- decode_stderr ---

def test_decode_stderr_empty():
    assert decode_stderr(b"") == ""
    assert decode_stderr(None) == ""

def test_decode_stderr_normal():
    result = decode_stderr(b"some warning\n")
    assert "some warning" in result

def test_decode_stderr_truncates():
    long_msg = b"x" * 5000
    result = decode_stderr(long_msg)
    assert "truncated" in result
    assert len(result) < 5000

# --- extract_stdout ---

def test_extract_stdout_empty():
    assert extract_stdout(b"") == ("", "")
    assert extract_stdout(b"   ") == ("", "")

def test_extract_stdout_json_only():
    json_str, user = extract_stdout(b'{"key": "value"}')
    assert json_str == '{"key": "value"}'
    assert user == ""

def test_extract_stdout_json_with_user_output():
    raw = b'Hello world\nDebug info\n{"result": 42}'
    json_str, user = extract_stdout(raw)
    assert json_str == '{"result": 42}'
    assert "Hello world" in user
    assert "Debug info" in user

def test_extract_stdout_array_json():
    json_str, user = extract_stdout(b'[1, 2, 3]')
    assert json_str == "[1, 2, 3]"

def test_extract_stdout_no_json():
    text, user = extract_stdout(b"just plain text")
    assert text == "just plain text"
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `.venv/bin/python -m pytest tests/test_errors.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'pyxel_mcp._errors')

- [ ] **Step 3: Create `_errors.py`**

Extract from `server.py` lines 30, 47-106 (`_MAX_STDERR`, `_decode_stderr`, `_ERROR_HINTS`, `_enrich_error`, `_extract_stdout`):

```python
"""Error handling utilities for pyxel-mcp."""

import re

_MAX_STDERR = 4000

_ERROR_HINTS = [
    (
        r"TypeError.*blt\(\)",
        "blt(x, y, img, u, v, w, h, [colkey], [rotate], [scale])."
        " img can be int 0-2 or an Image instance. Use colkey=0 for transparency.",
    ),
    (
        r"TypeError.*bltm\(\)",
        "bltm(x, y, tm, u, v, w, h, [colkey], [rotate], [scale]). u,v,w,h are in pixels."
        " tm can be int 0-7 or a Tilemap instance.",
    ),
    (
        r"IndexError.*(image|sound|music|tilemap)",
        "Default slots: images[0-2], tilemaps[0-7], sounds[0-63], musics[0-7]."
        " All lists are extensible via append()/slice assignment."
        " You can also create standalone instances with Image(), Sound(), etc.",
    ),
    (
        r"AttributeError.*module.*pyxel.*has no attribute",
        "Check API spelling. Common: btnp (not button_pressed),"
        " rndi (not randint), cls (not clear). Run pyxel_info for stubs.",
    ),
    (
        r"NameError.*name '(\w+)' is not defined",
        "If using a Pyxel constant like KEY_SPACE, use pyxel.KEY_SPACE.",
    ),
    (
        r"TypeError.*'int' object is not callable",
        "pyxel.mouse_x and pyxel.mouse_y are variables, not functions."
        " Use them without ().",
    ),
    (
        r"RecursionError",
        "Check that update()/draw() don't call pyxel.run() again."
        " Ensure __init__ doesn't create recursive instances.",
    ),
]


def enrich_error(text):
    """Append fix suggestions to common Pyxel error messages."""
    if not text:
        return text
    hints = []
    for pattern, suggestion in _ERROR_HINTS:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            hints.append(suggestion)
    if not hints:
        return text
    return text + "\n\nHint: " + " ".join(hints)


def decode_stderr(stderr):
    """Decode subprocess stderr, truncating if too long."""
    if not stderr:
        return ""
    text = stderr.decode(errors="replace").strip()
    if len(text) > _MAX_STDERR:
        text = text[:_MAX_STDERR] + "\n... (truncated)"
    return enrich_error(text)


def extract_stdout(raw_stdout):
    """Separate user print output from harness JSON in stdout.

    Returns (json_str, user_output). The harness always prints JSON as
    the last non-empty line. Everything before it is user print output.
    """
    text = raw_stdout.decode(errors="replace").strip()
    if not text:
        return "", ""
    lines = text.split("\n")
    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        if stripped.startswith(("{", "[")):
            json_str = stripped
            user_lines = lines[:i]
            user_output = "\n".join(user_lines).strip()
            return json_str, user_output
    return text, ""
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `.venv/bin/python -m pytest tests/test_errors.py -v`
Expected: All tests PASS

- [ ] **Step 5: Update server.py to import from _errors**

In `server.py`, replace `_decode_stderr`, `_enrich_error`, `_extract_stdout`, `_ERROR_HINTS`, `_MAX_STDERR` definitions with:

```python
from pyxel_mcp._errors import decode_stderr, enrich_error, extract_stdout
```

Remove lines 30, 47-127 from server.py (the error-related code). Update all call sites: `_decode_stderr` → `decode_stderr`, `_extract_stdout` → `extract_stdout`.

- [ ] **Step 6: Verify server still works**

Run: `.venv/bin/python -c "from pyxel_mcp.server import mcp; print('OK')"`
Expected: "OK"

- [ ] **Step 7: Commit**

```bash
git add src/pyxel_mcp/_errors.py tests/test_errors.py src/pyxel_mcp/server.py
git commit -m "Extract _errors module from server.py with tests"
```

---

## Task 3: Extract `_palette.py` + Tests

**Files:**
- Create: `src/pyxel_mcp/_palette.py`
- Create: `tests/test_palette.py`
- Modify: `src/pyxel_mcp/server.py` (remove `_PALETTE_NAMES`, `_PALETTE_RGB`, `_color_contrast`)

- [ ] **Step 1: Write tests**

```python
"""Tests for _palette module."""

from pyxel_mcp._palette import color_name, color_rgb, color_contrast, luminance, PALETTE


def test_palette_has_16_entries():
    assert len(PALETTE) == 16

def test_color_name_known():
    assert color_name(0) == "black"
    assert color_name(7) == "white"
    assert color_name(8) == "red"

def test_color_name_unknown():
    assert color_name(99) == "?"

def test_color_rgb_known():
    assert color_rgb(0) == (0, 0, 0)
    assert color_rgb(7) == (238, 238, 238)

def test_color_rgb_unknown():
    assert color_rgb(99) == (0, 0, 0)

def test_luminance_black():
    assert luminance(0) == 0.0

def test_luminance_white_high():
    assert luminance(7) > 200

def test_contrast_same_color():
    # Same color has ratio close to 1
    ratio = color_contrast(5, 5)
    assert ratio < 1.1

def test_contrast_black_white():
    # Maximum contrast
    ratio = color_contrast(0, 7)
    assert ratio > 10

def test_contrast_symmetric():
    assert color_contrast(3, 8) == color_contrast(8, 3)
```

- [ ] **Step 2: Run tests — verify fail**

Run: `.venv/bin/python -m pytest tests/test_palette.py -v`
Expected: FAIL

- [ ] **Step 3: Create `_palette.py`**

```python
"""Pyxel color palette data and utilities."""

PALETTE = {
    0: ("black", (0, 0, 0)),
    1: ("navy", (43, 51, 95)),
    2: ("purple", (126, 32, 114)),
    3: ("green", (25, 149, 56)),
    4: ("brown", (139, 72, 82)),
    5: ("dark_blue", (57, 92, 152)),
    6: ("light_blue", (169, 193, 255)),
    7: ("white", (238, 238, 238)),
    8: ("red", (212, 24, 108)),
    9: ("orange", (211, 132, 65)),
    10: ("yellow", (233, 195, 91)),
    11: ("lime", (112, 198, 169)),
    12: ("cyan", (118, 150, 222)),
    13: ("gray", (163, 163, 163)),
    14: ("pink", (255, 151, 152)),
    15: ("peach", (237, 199, 176)),
}


def color_name(idx):
    """Return color name for a palette index, or '?' if unknown."""
    entry = PALETTE.get(idx)
    return entry[0] if entry else "?"


def color_rgb(idx):
    """Return (r, g, b) for a palette index, or (0,0,0) if unknown."""
    entry = PALETTE.get(idx)
    return entry[1] if entry else (0, 0, 0)


def luminance(idx):
    """Compute perceived luminance (0-255) for a palette index."""
    r, g, b = color_rgb(idx)
    return 0.299 * r + 0.587 * g + 0.114 * b


def color_contrast(c1, c2):
    """Luminance contrast ratio between two palette indices."""
    lum1 = luminance(c1)
    lum2 = luminance(c2)
    lighter = max(lum1, lum2) + 0.05
    darker = min(lum1, lum2) + 0.05
    return lighter / darker
```

- [ ] **Step 4: Run tests — verify pass**

Run: `.venv/bin/python -m pytest tests/test_palette.py -v`
Expected: All PASS

- [ ] **Step 5: Update server.py**

Remove `_PALETTE_NAMES` (line ~1505-1510), `_PALETTE_RGB` (line ~2291-2296), `_color_contrast` (line ~2299-2307). Replace with:

```python
from pyxel_mcp._palette import color_name, color_contrast, PALETTE
```

Update all references: `_PALETTE_NAMES.get(c, "?")` → `color_name(c)`, `_color_contrast(...)` → `color_contrast(...)`.

- [ ] **Step 6: Verify server**

Run: `.venv/bin/python -c "from pyxel_mcp.server import mcp; print('OK')"`
Expected: "OK"

- [ ] **Step 7: Commit**

```bash
git add src/pyxel_mcp/_palette.py tests/test_palette.py src/pyxel_mcp/server.py
git commit -m "Extract _palette module from server.py with tests"
```

---

## Task 4: Extract `_audio.py` with numpy + Tests

**Files:**
- Create: `src/pyxel_mcp/_audio.py`
- Create: `tests/test_audio.py`
- Modify: `src/pyxel_mcp/server.py` (remove audio analysis code)

- [ ] **Step 1: Write tests**

```python
"""Tests for _audio module."""

import math
import numpy as np
from pyxel_mcp._audio import (
    freq_to_note, freq_to_midi, estimate_freq,
    detect_key, analyze_intervals, suggest_role, analyze_wav,
)

# --- freq_to_note ---

def test_freq_to_note_a4():
    assert freq_to_note(440.0) == "A4"

def test_freq_to_note_c4():
    assert freq_to_note(261.63) == "C4"

def test_freq_to_note_silence():
    assert freq_to_note(0) == "~"
    assert freq_to_note(10) == "~"

# --- freq_to_midi ---

def test_freq_to_midi_a4():
    assert freq_to_midi(440.0) == 69

def test_freq_to_midi_c4():
    assert freq_to_midi(261.63) == 60

def test_freq_to_midi_silence():
    assert freq_to_midi(0) == -1

# --- estimate_freq (numpy FFT) ---

def test_estimate_freq_440hz():
    sr = 44100
    t = np.arange(sr // 10) / sr  # 100ms
    samples = np.sin(2 * np.pi * 440 * t)
    freq = estimate_freq(samples, sr)
    assert abs(freq - 440) < 10, f"Expected ~440Hz, got {freq}"

def test_estimate_freq_261hz():
    sr = 44100
    t = np.arange(sr // 10) / sr
    samples = np.sin(2 * np.pi * 261.63 * t)
    freq = estimate_freq(samples, sr)
    assert abs(freq - 261.63) < 10, f"Expected ~261Hz, got {freq}"

def test_estimate_freq_silence():
    samples = np.zeros(4410)
    assert estimate_freq(samples, 44100) == 0

# --- detect_key ---

def test_detect_key_c_major():
    # C major scale MIDI notes: C4 D4 E4 F4 G4 A4 B4
    midi = [60, 62, 64, 65, 67, 69, 71]
    key = detect_key(midi)
    assert "C" in key and "major" in key

def test_detect_key_empty():
    assert detect_key([]) == "unknown"

# --- analyze_intervals ---

def test_analyze_intervals_steps():
    midi = [60, 62, 64, 65]  # all steps (1-2 semitones)
    result = analyze_intervals(midi)
    assert result["step (1-2)"] == 3

def test_analyze_intervals_single():
    assert analyze_intervals([60]) == {}

# --- suggest_role ---

def test_suggest_role_bass():
    midi = [36, 38, 40]  # C2-E2, low
    assert "bass" in suggest_role(midi, [100, 100, 100])

def test_suggest_role_melody():
    midi = [72, 74, 76, 72, 71]  # C5+, high, varied
    assert "melody" in suggest_role(midi, [100, 200, 150, 100, 300])

def test_suggest_role_empty():
    assert suggest_role([], []) == "silent"
```

- [ ] **Step 2: Run tests — verify fail**

Run: `.venv/bin/python -m pytest tests/test_audio.py -v`
Expected: FAIL

- [ ] **Step 3: Create `_audio.py`**

Rewrite from `server.py` lines 1131-1393, replacing pure-Python autocorrelation with numpy FFT:

```python
"""WAV audio analysis with numpy-accelerated frequency estimation."""

import math
import struct
import wave

import numpy as np

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

_SCALE_TEMPLATES = {
    "major": {0, 2, 4, 5, 7, 9, 11},
    "minor": {0, 2, 3, 5, 7, 8, 10},
    "penta": {0, 2, 4, 7, 9},
}


def freq_to_note(freq):
    """Convert frequency (Hz) to note name like C5, A4."""
    if freq < 20:
        return "~"
    midi = 69 + 12 * math.log2(freq / 440.0)
    idx = round(midi) % 12
    octave = (round(midi) // 12) - 1
    return f"{NOTE_NAMES[idx]}{octave}"


def freq_to_midi(freq):
    """Convert frequency to MIDI note number."""
    if freq < 20:
        return -1
    return round(69 + 12 * math.log2(freq / 440.0))


def estimate_freq(samples, sample_rate):
    """Estimate fundamental frequency using FFT-based autocorrelation.

    ~50-100x faster than pure-Python autocorrelation.
    """
    n = len(samples)
    if n < 50:
        return 0

    min_lag = max(1, sample_rate // 2000)  # up to 2000 Hz
    max_lag = min(sample_rate // 50, n // 2)  # down to 50 Hz
    if max_lag <= min_lag:
        return 0

    # Remove DC offset
    samples = samples - np.mean(samples)
    energy = np.dot(samples, samples)
    if energy == 0:
        return 0

    # FFT-based autocorrelation: R(lag) = IFFT(|FFT(x)|^2)
    fft_size = 1
    while fft_size < 2 * n:
        fft_size *= 2
    f = np.fft.rfft(samples, fft_size)
    acf = np.fft.irfft(f * np.conj(f))[:n]
    acf /= acf[0]  # normalize

    # Extract lag range
    corrs = acf[min_lag:max_lag]
    if len(corrs) == 0:
        return 0

    # Find where correlation first drops below threshold (end of initial decay)
    dip_idx = None
    for i in range(len(corrs)):
        if corrs[i] < 0.2:
            dip_idx = i
            break

    if dip_idx is None:
        best_i = np.argmax(corrs)
        return sample_rate / (min_lag + best_i) if corrs[best_i] > 0.6 else 0

    # Find first peak after the dip (the true fundamental period)
    for i in range(max(1, dip_idx), len(corrs) - 1):
        if corrs[i] > 0.3 and corrs[i] >= corrs[i - 1] and corrs[i] >= corrs[i + 1]:
            return sample_rate / (min_lag + i)

    return 0


def detect_key(midi_notes):
    """Detect musical key from a list of MIDI note numbers."""
    if not midi_notes:
        return "unknown"
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


def analyze_intervals(midi_notes):
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


def suggest_role(midi_notes, durations_ms):
    """Suggest channel role based on pitch range and rhythm."""
    if not midi_notes:
        return "silent"
    avg = sum(midi_notes) / len(midi_notes)
    unique_durs = len(set(durations_ms))

    if avg < 48:
        return "bass"
    if avg < 60:
        return "bass" if unique_durs <= 2 else "bass/accompaniment"
    if avg < 72:
        return "melody" if unique_durs >= 3 else "accompaniment"
    return "melody (high)"


def analyze_wav(wav_path):
    """Analyze WAV file, return frequency/amplitude report with musical analysis.

    Uses numpy for vectorized sample parsing and FFT-based frequency estimation.
    """
    with wave.open(wav_path, "r") as wf:
        n_channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if n_frames == 0:
        return "Empty audio (0 samples)"

    # Parse samples with numpy (much faster than struct.unpack)
    samples = np.frombuffer(raw, dtype=np.int16)
    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1).astype(np.int16)

    duration = n_frames / sample_rate
    peak = int(np.max(np.abs(samples)))
    rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))

    # Time-windowed analysis (100ms windows)
    window_size = sample_rate // 10
    segments = []
    for start in range(0, len(samples), window_size):
        w = samples[start:start + window_size].astype(np.float64)
        if len(w) < 50:
            break
        w_rms = float(np.sqrt(np.mean(w ** 2)))
        if w_rms < 50:
            segments.append(("~", 0, w_rms))
            continue
        freq = estimate_freq(w, sample_rate)
        note = freq_to_note(freq) if freq > 0 else "~"
        segments.append((note, freq, w_rms))

    # Group consecutive identical notes
    grouped = []
    for note, freq, w_rms in segments:
        if grouped and grouped[-1][0] == note:
            grouped[-1] = (
                note, freq,
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

    # Musical analysis
    played = [(n, f, r, d) for n, f, r, d in grouped if n != "~"]
    if played:
        midi_notes = [freq_to_midi(f) for _, f, _, _ in played if f > 0]
        durations = [d for _, _, _, d in played]

        if midi_notes:
            lo_note = freq_to_note(min(f for _, f, _, _ in played if f > 0))
            hi_note = freq_to_note(max(f for _, f, _, _ in played if f > 0))
            semitone_range = max(midi_notes) - min(midi_notes)

            lines.append("")
            lines.append("Musical analysis:")
            lines.append(
                f"  Pitch range: {lo_note} - {hi_note}"
                f" ({semitone_range} semitones)"
            )

            note_counts = {}
            for n, _, _, _ in played:
                note_counts[n] = note_counts.get(n, 0) + 1
            top_notes = sorted(note_counts.items(), key=lambda x: -x[1])[:6]
            lines.append(
                "  Top notes: "
                + " ".join(f"{n}({c}x)" for n, c in top_notes)
            )

            key = detect_key(midi_notes)
            lines.append(f"  Key estimate: {key}")

            intervals = analyze_intervals(midi_notes)
            if intervals:
                total = sum(intervals.values())
                parts = []
                for label, count in intervals.items():
                    if count > 0:
                        pct = count * 100 // total
                        parts.append(f"{label}:{pct}%")
                lines.append(f"  Intervals: {' '.join(parts)}")

            dur_counts = {}
            for d in durations:
                dur_counts[d] = dur_counts.get(d, 0) + 1
            top_durs = sorted(dur_counts.items(), key=lambda x: -x[1])[:4]
            lines.append(
                "  Rhythm: "
                + " ".join(f"{d}ms({c}x)" for d, c in top_durs)
            )

            role = suggest_role(midi_notes, durations)
            lines.append(f"  Suggested role: {role}")

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests — verify pass**

Run: `.venv/bin/python -m pytest tests/test_audio.py -v`
Expected: All PASS

- [ ] **Step 5: Update server.py**

Remove lines 1131-1393 (NOTE_NAMES through _analyze_wav). Replace with:

```python
from pyxel_mcp._audio import analyze_wav
```

Update call site in `render_audio`: `_analyze_wav` → `analyze_wav`.

- [ ] **Step 6: Verify server**

Run: `.venv/bin/python -c "from pyxel_mcp.server import mcp; print('OK')"`
Expected: "OK"

- [ ] **Step 7: Commit**

```bash
git add src/pyxel_mcp/_audio.py tests/test_audio.py src/pyxel_mcp/server.py
git commit -m "Extract _audio module with numpy FFT acceleration"
```

---

## Task 5: Extract `_validate.py` + Tests

**Files:**
- Create: `src/pyxel_mcp/_validate.py`
- Create: `tests/test_validate.py`
- Modify: `src/pyxel_mcp/server.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for _validate module."""

from pyxel_mcp._validate import validate_source

def test_valid_script():
    src = '''
import pyxel
class App:
    def __init__(self):
        pyxel.init(160, 120)
        pyxel.run(self.update, self.draw)
    def update(self):
        pass
    def draw(self):
        pyxel.cls(0)
App()
'''
    result = validate_source(src, "test.py")
    assert "No issues" in result

def test_syntax_error():
    result = validate_source("def foo(\n", "bad.py")
    assert "Syntax error" in result

def test_missing_import():
    result = validate_source("pyxel.init(160, 120)\npyxel.show()", "t.py")
    assert "import pyxel" in result

def test_missing_init():
    result = validate_source("import pyxel\npyxel.show()", "t.py")
    assert "pyxel.init()" in result

def test_missing_game_loop():
    result = validate_source("import pyxel\npyxel.init(160,120)", "t.py")
    assert "run()" in result or "show()" in result

def test_run_in_draw():
    src = '''
import pyxel
class App:
    def __init__(self):
        pyxel.init(160,120)
        pyxel.run(self.update, self.draw)
    def update(self): pass
    def draw(self):
        pyxel.cls(0)
        pyxel.run(self.update, self.draw)
'''
    result = validate_source(src, "t.py")
    assert "draw()" in result and "run()" in result

def test_math_sin_warning():
    src = "import pyxel\nimport math\npyxel.init(160,120)\nx=math.sin(1)\npyxel.show()"
    result = validate_source(src, "t.py")
    assert "degrees" in result

def test_no_cls_in_draw():
    src = '''
import pyxel
class App:
    def __init__(self):
        pyxel.init(160,120)
        pyxel.run(self.update, self.draw)
    def update(self): pass
    def draw(self):
        pyxel.rect(0,0,10,10,7)
'''
    result = validate_source(src, "t.py")
    assert "cls" in result

def test_list_mutation_warning():
    src = '''
import pyxel
pyxel.init(160,120)
enemies = []
for e in enemies:
    enemies.remove(e)
pyxel.show()
'''
    result = validate_source(src, "t.py")
    assert "remove" in result.lower() or "mutation" in result.lower() or "iterat" in result.lower()
```

- [ ] **Step 2: Run tests — verify fail**

Run: `.venv/bin/python -m pytest tests/test_validate.py -v`
Expected: FAIL

- [ ] **Step 3: Create `_validate.py`**

Extract from `server.py` lines 2170-2285, adding new anti-patterns:

```python
"""Script validation for Pyxel programs."""

import ast
import re

PYXEL_ANTIPATTERNS = [
    (
        r"pyxel\.run\s*\(",
        "draw",
        "pyxel.run() called inside draw(). Move it to __init__.",
    ),
    (
        r"pyxel\.init\s*\(",
        "update",
        "pyxel.init() called inside update(). Move it to __init__.",
    ),
    (
        r"pyxel\.init\s*\(",
        "draw",
        "pyxel.init() called inside draw(). Move it to __init__.",
    ),
    (
        r"math\.sin\b|math\.cos\b",
        None,
        "Using math.sin/cos (radians). Pyxel's pyxel.sin/cos use degrees.",
    ),
    (
        r"random\.randint\b",
        None,
        "Using random.randint. Prefer pyxel.rndi(a, b) for Pyxel games.",
    ),
    (
        r"for\s+\w+\s+in\s+(\w+)\s*:.*\n\s+\1\.remove\(",
        None,
        "Mutating list while iterating. Use: for e in list(items): items.remove(e)",
    ),
]


def validate_source(source, filename="script.py"):
    """Validate Pyxel script source code. Returns report string."""
    issues = []

    # Syntax check
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as e:
        return f"Syntax error at line {e.lineno}: {e.msg}"

    # Collect function/method bodies
    method_bodies = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno
            end = node.end_lineno or start
            body_lines = source.split("\n")[start - 1:end]
            method_bodies[node.name] = "\n".join(body_lines)

    # Anti-pattern checks
    for pattern, context, message in PYXEL_ANTIPATTERNS:
        text = method_bodies.get(context, "") if context else source
        if re.search(pattern, text, re.DOTALL):
            issues.append(message)

    # Missing import
    if not re.search(r"import\s+pyxel|from\s+pyxel", source):
        issues.append("No 'import pyxel' found.")

    # Missing init
    if not re.search(r"pyxel\.init\s*\(", source):
        issues.append("No pyxel.init() call found.")

    # Missing game loop
    has_run = bool(re.search(r"pyxel\.run\s*\(", source))
    has_show = bool(re.search(r"pyxel\.show\s*\(", source))
    has_flip = bool(re.search(r"pyxel\.flip\s*\(", source))
    if not (has_run or has_show or has_flip):
        issues.append("No pyxel.run(), show(), or flip() call found.")

    # Missing cls in draw
    if "draw" in method_bodies:
        if not re.search(r"pyxel\.cls\s*\(|cls\s*\(", method_bodies["draw"]):
            issues.append("draw() may be missing pyxel.cls(). Screen won't clear.")

    # Stats
    n_classes = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
    n_functions = sum(1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    n_lines = len(source.split("\n"))

    report = f"Script: {filename}"
    report += f"  ({n_lines} lines, {n_classes} classes, {n_functions} functions)"

    if issues:
        report += f"\n\nWarnings ({len(issues)}):"
        for issue in issues:
            report += f"\n  - {issue}"
    else:
        report += "\n\nNo issues found."

    return report
```

- [ ] **Step 4: Run tests — verify pass**

Run: `.venv/bin/python -m pytest tests/test_validate.py -v`
Expected: All PASS

- [ ] **Step 5: Update server.py**

Remove `_PYXEL_ANTIPATTERNS` and `validate_script` logic body. Replace with:

```python
from pyxel_mcp._validate import validate_source
```

The `validate_script` tool function reads the file and calls `validate_source(source, basename)`.

- [ ] **Step 6: Verify + Commit**

```bash
.venv/bin/python -c "from pyxel_mcp.server import mcp; print('OK')"
git add src/pyxel_mcp/_validate.py tests/test_validate.py src/pyxel_mcp/server.py
git commit -m "Extract _validate module with new anti-patterns"
```

---

## Task 6: Extract `_format.py` + Tests

**Depends on:** Task 3 (`_palette.py` — imports `color_name`)

**Files:**
- Create: `src/pyxel_mcp/_format.py`
- Create: `tests/test_format.py`
- Modify: `src/pyxel_mcp/server.py`

- [ ] **Step 1: Write tests**

Test each formatter with sample JSON data matching harness output format. Verify output contains expected strings (screen size, color names, symmetry, frame numbers, etc). Test the `=== Analysis ===` / `=== Suggestions ===` unified format.

- [ ] **Step 2: Run tests — verify fail**

Run: `.venv/bin/python -m pytest tests/test_format.py -v`

- [ ] **Step 3: Create `_format.py`**

Move `_format_sprite_report`, `_format_layout_report`, `_format_state_report`, `_format_state_timeline` from server.py. Import `color_name` from `_palette`. Add unified output format with `=== Analysis ===` / `=== Suggestions ===` sections.

- [ ] **Step 4: Run tests — verify pass**

- [ ] **Step 5: Update server.py, verify, commit**

```bash
git commit -m "Extract _format module with unified output format"
```

---

## Task 7: Extract `_subprocess.py` + Extract `instructions.md`

**Depends on:** Task 2 (`_errors.py` — imports `decode_stderr`, `extract_stdout`)

**Files:**
- Create: `src/pyxel_mcp/_subprocess.py`
- Create: `tests/test_subprocess.py`
- Create: `src/pyxel_mcp/instructions.md`
- Modify: `src/pyxel_mcp/server.py`

- [ ] **Step 1: Create `_subprocess.py`**

```python
"""Subprocess execution for MCP tool harnesses."""

import asyncio
import json
import os
import sys

from pyxel_mcp._errors import decode_stderr, extract_stdout

_PKG_DIR = os.path.dirname(__file__)

HARNESS_PATHS = {
    "run": os.path.join(_PKG_DIR, "harness.py"),
    "audio": os.path.join(_PKG_DIR, "audio_harness.py"),
    "sprite": os.path.join(_PKG_DIR, "sprite_harness.py"),
    "frames": os.path.join(_PKG_DIR, "frames_harness.py"),
    "layout": os.path.join(_PKG_DIR, "layout_harness.py"),
    "input": os.path.join(_PKG_DIR, "input_harness.py"),
    "state": os.path.join(_PKG_DIR, "state_harness.py"),
    "screen": os.path.join(_PKG_DIR, "screen_harness.py"),
    "tilemap": os.path.join(_PKG_DIR, "tilemap_harness.py"),
    "bank": os.path.join(_PKG_DIR, "bank_harness.py"),
}


async def run_harness(harness_name, args, *, cwd, timeout=10):
    """Run a harness subprocess and return (json_data, user_output, stderr_text).

    Raises asyncio.TimeoutError on timeout, RuntimeError on non-zero exit.
    Returns (None, user_output, stderr_text) when no JSON in stdout.
    """
    harness_path = HARNESS_PATHS[harness_name]
    proc = await asyncio.create_subprocess_exec(
        sys.executable, harness_path, *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    stdout, stderr = await asyncio.wait_for(
        proc.communicate(), timeout=timeout
    )

    stderr_text = decode_stderr(stderr)

    if proc.returncode != 0:
        error_msg = stderr_text or "Unknown error"
        raise RuntimeError(
            f"Harness failed (exit code {proc.returncode}): {error_msg}"
        )

    json_data = None
    user_output = ""
    if stdout:
        json_str, user_output = extract_stdout(stdout)
        if json_str:
            json_data = json.loads(json_str)

    return json_data, user_output, stderr_text
```

- [ ] **Step 2: Extract `instructions.md`**

Copy `_INSTRUCTIONS` string (server.py lines 130-1039) to `src/pyxel_mcp/instructions.md` as raw Markdown.

- [ ] **Step 3: Write `tests/test_subprocess.py`**

Test `run_harness` with a mock subprocess (use `unittest.mock.patch` on `asyncio.create_subprocess_exec`). Test: successful JSON return, non-zero exit raises RuntimeError, timeout raises TimeoutError, harness path registry has all 10 entries.

- [ ] **Step 4: Run subprocess tests — verify pass**

Run: `.venv/bin/python -m pytest tests/test_subprocess.py -v`

- [ ] **Step 5: Update server.py**

Replace all `HARNESS_PATH` constants (lines 19-28) and inline subprocess calls with `run_harness`. Replace `_INSTRUCTIONS` with file loading. No `pyproject.toml` changes needed — `instructions.md` inside `src/pyxel_mcp/` is automatically included by hatchling's `packages` setting.

- [ ] **Step 6: Verify all imports work**

Run: `.venv/bin/python -c "from pyxel_mcp.server import mcp; print('OK')"`

- [ ] **Step 7: Run all existing tests**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 8: Commit**

```bash
git add src/pyxel_mcp/_subprocess.py tests/test_subprocess.py src/pyxel_mcp/instructions.md src/pyxel_mcp/server.py
git commit -m "Extract _subprocess module and instructions.md, slim server.py"
```

---

## Task 8: Expand `_headless.py` — Harness Infrastructure

**Files:**
- Modify: `src/pyxel_mcp/_headless.py`
- Create: `tests/test_headless.py`

- [ ] **Step 1: Write tests for new helpers**

Test `init_harness` argument parsing (mock sys.argv), `patch_game_loop` callback mechanism, `noop_game_loop`. These tests don't import pyxel — test the arg parsing and callback wiring only.

- [ ] **Step 2: Run tests — verify fail**

- [ ] **Step 3: Implement expanded `_headless.py`**

Add `init_harness(*arg_names)`, `patch_game_loop(on_update_frame, on_show)`, `noop_game_loop()` to the existing `_headless.py` while keeping `patch_headless_init` and `run_script`.

- [ ] **Step 4: Run tests — verify pass**

- [ ] **Step 5: Commit**

```bash
git commit -m "Expand _headless.py with harness boilerplate helpers"
```

---

## Task 9: Refactor All Harnesses

**Files:**
- Modify: all 10 harness files
- Create: `tests/test_layout_analysis.py`

Rewrite each harness using `init_harness`, `patch_game_loop`/`noop_game_loop`, `run_script`.

- [ ] **Step 1: Refactor `harness.py` (simplest, proves the pattern)**

Rewrite to ~30 lines using `init_harness` + `patch_game_loop`.

- [ ] **Step 2: Verify `run_and_capture` still works**

Run: `.venv/bin/python -c "from pyxel_mcp.server import mcp; print('OK')"`

- [ ] **Step 3: Refactor `audio_harness.py` and `sprite_harness.py`**

These use `noop_game_loop` since they don't need the game loop.

- [ ] **Step 4: Refactor `frames_harness.py`, `screen_harness.py`, `tilemap_harness.py`, `bank_harness.py`**

All follow the same `patch_game_loop` pattern with frame-based capture.

- [ ] **Step 5: Refactor `state_harness.py`**

Similar pattern but captures App instance from `pyxel.run` args.

- [ ] **Step 6: Refactor `input_harness.py`**

Most complex — keeps its input simulation logic but uses shared boilerplate.

- [ ] **Step 7: Decompose `layout_harness.py`**

Split `_analyze_and_quit` into `read_pixels`, `find_bg_color`, `content_bbox`, `calc_balance`, `calc_margins`, `detect_text`, `merge_text_spans`, `dedup_text_by_y`, `analyze_text_alignment`. Keep these as module-level functions (testable without Pyxel).

- [ ] **Step 8: Write `tests/test_layout_analysis.py`**

Test each decomposed function with synthetic pixel grids. Test text detection with known patterns, balance calculation with symmetric/asymmetric grids.

- [ ] **Step 9: Run all tests**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 10: Commit**

```bash
git add src/pyxel_mcp/*_harness.py src/pyxel_mcp/harness.py tests/test_layout_analysis.py
git commit -m "Refactor all harnesses using shared _headless helpers"
```

---

## Task 10: Graphics Enhancement — inspect_sprite

**Files:**
- Modify: `src/pyxel_mcp/sprite_harness.py` (add analysis to output)
- Modify: `src/pyxel_mcp/_format.py` (enhance `format_sprite_report`)

- [ ] **Step 1: Add sprite analysis to harness output**

Extend sprite_harness JSON output with: outline completeness, fill ratio, edge/center luminance for pillow shading detection, empty region scan.

- [ ] **Step 2: Enhance `format_sprite_report` in `_format.py`**

Add outline gap warnings, color count validation (3-4 for 8x8, 5-6 for 16x16), pillow shading detection, material hints, empty space report. Use `=== Analysis ===` / `=== Suggestions ===` format.

- [ ] **Step 3: Write tests for new sprite analysis**

- [ ] **Step 4: Verify with real sprite, commit**

```bash
git commit -m "Enhance inspect_sprite: outline, color count, pillow shading"
```

---

## Task 11: Graphics Enhancement — inspect_palette

**Files:**
- Modify: `src/pyxel_mcp/_format.py` (add `format_palette_report`)
- Modify: `src/pyxel_mcp/_palette.py` (add WCAG contrast, hierarchy analysis)

- [ ] **Step 1: Add WCAG-style relative luminance to `_palette.py`**

Replace simple brightness with sRGB relative luminance per WCAG 2.0 spec.

- [ ] **Step 2: Add color hierarchy analysis**

Classify used colors into background/environment/interactive layers. Score conformance.

- [ ] **Step 3: Add color role estimation and suggestions**

Auto-classify roles, suggest unused colors for improvement.

- [ ] **Step 4: Update tests, verify, commit**

```bash
git commit -m "Enhance inspect_palette: WCAG contrast, hierarchy, suggestions"
```

---

## Task 12: Graphics Enhancement — inspect_layout

**Files:**
- Modify: `src/pyxel_mcp/layout_harness.py`
- Modify: `src/pyxel_mcp/_format.py`

- [ ] **Step 1: Add font height auto-estimation**

Detect actual font height from pixel continuity instead of hardcoded FONT_H=6.

- [ ] **Step 2: Add UI element detection**

Detect rectangular frames (panels, buttons) by looking for single-color rectangles.

- [ ] **Step 3: Add grid alignment check**

Check if content boundaries align to 8px or 16px grid.

- [ ] **Step 4: Update `format_layout_report` with suggestions**

Use unified output format. Add actionable suggestions.

- [ ] **Step 5: Update tests, verify, commit**

```bash
git commit -m "Enhance inspect_layout: font detection, UI elements, grid alignment"
```

---

## Task 13: New Tool — inspect_animation

**Files:**
- Modify: `src/pyxel_mcp/sprite_harness.py` (support multi-region read)
- Modify: `src/pyxel_mcp/server.py` (add tool function)
- Modify: `src/pyxel_mcp/_format.py` (add animation report formatter)

- [ ] **Step 1: Extend sprite_harness for multi-region reads**

Accept additional args for frame_count, read adjacent horizontal regions.

- [ ] **Step 2: Add `inspect_animation` tool to server.py**

Call sprite_harness with multi-region args, format consistency report.

- [ ] **Step 3: Add `format_animation_report` to `_format.py`**

Report palette consistency, silhouette size variance, pixel change rate.

- [ ] **Step 4: Write tests, verify, commit**

```bash
git commit -m "Add inspect_animation tool for sprite sheet consistency"
```

---

## Task 14: validate_script Enhancement

**Files:**
- Modify: `src/pyxel_mcp/_validate.py`
- Modify: `tests/test_validate.py`

- [ ] **Step 1: Add new anti-patterns to `PYXEL_ANTIPATTERNS`**

```python
# blt() without colkey — warn only if there's a visible sprite draw,
# not for tilemap or screen operations. Match: pyxel.blt( with no colkey= arg.
(
    r"pyxel\.blt\([^)]*\)(?<!colkey)",
    None,
    "blt() without colkey. Add colkey=0 for transparent backgrounds.",
),
# pyxel.run() outside __init__ (top-level or in other methods)
(
    r"pyxel\.run\s*\(",
    None,  # check in ALL code, then exclude __init__
    "pyxel.run() found outside __init__. It should only be called once in __init__.",
),
```

Note: `blt()` without `colkey` detection uses a heuristic — `colkey` is optional and sometimes intentionally omitted (e.g., full-rectangle draws). Emit as "Tip" not "Warning". The `pyxel.run()` outside `__init__` check needs special handling: search globally, then verify it's not inside `__init__`.

- [ ] **Step 2: Write tests for each new pattern**

Test both detection and non-detection (no false positives on valid code that intentionally omits `colkey` for full-rect blt).

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "Expand validate_script anti-pattern coverage"
```

---

## Task 15: Integration Tests

**Files:**
- Create: `tests/test_tools.py`

- [ ] **Step 1: Write integration tests**

Create minimal Pyxel scripts in temp files. Test `run_and_capture` returns an Image, `validate_script` catches errors, `inspect_screen` returns grid data, `render_audio` returns analysis text.

```python
"""Integration tests for MCP tools (require Pyxel)."""

import asyncio
import os
import tempfile
import pytest

MINIMAL_SCRIPT = '''\
import pyxel
pyxel.init(32, 32)
pyxel.cls(1)
pyxel.rect(4, 4, 24, 24, 8)
pyxel.show()
'''

@pytest.fixture
def script_path():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(MINIMAL_SCRIPT)
        path = f.name
    yield path
    os.unlink(path)

@pytest.mark.asyncio
async def test_run_and_capture(script_path):
    from pyxel_mcp.server import run_and_capture
    result = await run_and_capture(script_path, frames=1, scale=1, timeout=10)
    # Should return list with an Image and info string
    assert len(result) >= 2
    assert "Captured" in result[-1]

@pytest.mark.asyncio
async def test_validate_script(script_path):
    from pyxel_mcp.server import validate_script
    result = await validate_script(script_path)
    assert "No issues" in result or "Warning" in result

@pytest.mark.asyncio
async def test_inspect_screen(script_path):
    from pyxel_mcp.server import inspect_screen
    result = await inspect_screen(script_path, frames=1, timeout=10)
    assert "32x32" in result
```

- [ ] **Step 2: Run integration tests**

Run: `.venv/bin/python -m pytest tests/test_tools.py -v`
Expected: All PASS (requires Pyxel + display/headless)

- [ ] **Step 3: Commit**

```bash
git commit -m "Add integration tests for MCP tools"
```

---

## Task 16: Final Verification and Cleanup

- [ ] **Step 1: Run full test suite**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 2: Verify server starts**

Run: `.venv/bin/python -m pyxel_mcp.server`
Expected: MCP server starts without errors (Ctrl+C to stop)

- [ ] **Step 3: Check line counts**

Verify server.py is ~300 lines. Verify harness reductions match estimates.

- [ ] **Step 4: Update instructions.md "Reading Tool Output" section**

Update to reflect new unified output format (`=== Analysis ===` / `=== Suggestions ===`).

- [ ] **Step 5: Final commit**

```bash
git commit -m "Final cleanup: update instructions, verify line counts"
```
