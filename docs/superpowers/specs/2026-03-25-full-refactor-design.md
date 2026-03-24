# Pyxel MCP Full Refactor Design

## Goal

Comprehensive refactoring of all files: improve maintainability, add test
infrastructure, significantly boost WAV analysis performance, and enhance
graphics/design analysis tools. Breaking changes to tool interfaces are
acceptable.

## Phase 1: Common Infrastructure

### 1a. Expand `_headless.py` — Harness Boilerplate Elimination

All 10 harnesses repeat the same pattern: arg parse, sys.argv reset, pyxel
import, headless init, patch run/show/flip. Extract into shared helpers.

**New functions:**

```python
def init_harness(*arg_names: str) -> tuple[str, dict]:
    """Parse positional CLI args, reset sys.argv, import+patch pyxel.

    Each harness has different args (harness: 4, input: 5+json, audio: 3-5).
    arg_names defines the expected positional args after script_path.
    Returns (script_path, {name: value} dict).
    """

def patch_game_loop(on_update_frame, on_show=None):
    """Patch pyxel.run/show/flip with unified capture pattern.
    on_update_frame(frame_count, draw) -> bool: return True to exit.
    on_show(): called on pyxel.show(). Default: exit.
    """

def noop_game_loop():
    """Patch run/show/flip to no-ops for resource-only harnesses.
    Used by audio_harness and sprite_harness which only need resource
    setup without running the game loop.
    """
```

### 1b. New `_palette.py` — Unified Palette Data

Merge `_PALETTE_NAMES` and `_PALETTE_RGB` (currently scattered in server.py)
into a single module.

```python
PALETTE = {
    0: ("black", (0, 0, 0)),
    1: ("navy", (43, 51, 95)),
    ...
}

def color_name(idx: int) -> str: ...
def color_rgb(idx: int) -> tuple[int, int, int]: ...
def color_contrast(c1: int, c2: int) -> float: ...
def luminance(idx: int) -> float: ...
```

### 1c. New `_subprocess.py` — Server-Side Subprocess Runner

Each tool function in server.py repeats: create_subprocess_exec, wait_for,
extract_stdout, decode_stderr, handle timeout. Consolidate.

```python
async def run_harness(
    harness_path: str,
    args: list[str],
    *,
    cwd: str,
    timeout: int = 10,
) -> tuple[Any, str, str]:
    """Run harness subprocess, return (json_data, user_output, stderr_text).
    Raises TimeoutError, RuntimeError on failure.
    """
```

## Phase 2: Split server.py

Current: 2750 lines. Target: ~300 lines for server.py proper.

### New Module Structure

```
src/pyxel_mcp/
  server.py          # MCP server — tool registration only (~300 lines)
  _headless.py       # Expanded: harness common infra
  _palette.py        # Palette data + color calculations
  _subprocess.py     # Subprocess execution
  _audio.py          # WAV analysis + music theory (~200 lines)
  _format.py         # Report formatters (~250 lines)
  _validate.py       # Script validation logic (~100 lines)
  _errors.py         # Error hints + stderr processing (~50 lines)
  instructions.md    # _INSTRUCTIONS extracted to external file (910 lines)
```

### Module Responsibilities

- **server.py**: `FastMCP` instance, `@mcp.tool()` functions. Each is a thin
  wrapper: `run_harness()` + formatter.
- **_palette.py**: `PALETTE` dict, `color_name`, `color_rgb`,
  `color_contrast`, `luminance`. Used by `_format.py` and tool functions.
- **_audio.py**: `estimate_freq`, `freq_to_note`, `detect_key`,
  `analyze_intervals`, `suggest_role`, `analyze_wav`.
- **_format.py**: `format_sprite_report`, `format_layout_report`,
  `format_state_report`, `format_state_timeline`.
- **_validate.py**: `PYXEL_ANTIPATTERNS` + validation logic.
- **_errors.py**: `ERROR_HINTS`, `enrich_error`, `decode_stderr`,
  `extract_stdout`.
- **_subprocess.py**: `run_harness` + harness path registry.

### Instructions Loading

```python
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
```

## Phase 3: WAV Analysis Performance

### Problem

`_estimate_freq` uses pure-Python autocorrelation: O(n²) nested loops.
100ms window at 44100Hz = 4410 samples, ~860 lags. Per window: ~3.4M
float ops. 10s WAV (100 windows): ~340M total operations.

### Solution: numpy as Direct Dependency

Add `numpy` to `pyproject.toml` dependencies. Use FFT-based
autocorrelation:

```python
import numpy as np

def estimate_freq(samples: np.ndarray, sample_rate: int) -> float:
    """FFT-based autocorrelation for ~50-100x speedup."""
    n = len(samples)
    fft_size = 1
    while fft_size < 2 * n:
        fft_size *= 2
    # R(lag) = IFFT(|FFT(x)|^2)
    f = np.fft.rfft(samples, fft_size)
    acf = np.fft.irfft(f * np.conj(f))[:n]
    acf /= acf[0]  # normalize
    # Peak detection in lag range [min_lag, max_lag]
    ...
```

### Additional Performance Improvements

- Downsample 44100Hz → 8000Hz before analysis (5.5x fewer samples).
  Note: Nyquist limit becomes 4000Hz. Pyxel sounds rarely exceed this
  (C8 = 4186Hz), but noise-based SE may lose high-frequency detail.
  This is acceptable since `estimate_freq` targets fundamental pitch.
- Use `np.frombuffer` for WAV sample parsing (skip struct.unpack)
- Vectorize `_analyze_wav` window processing

### Expected Speedup

~50-100x for frequency estimation. Overall `_analyze_wav`: ~20-50x.

## Phase 4: Harness Refactoring

### Boilerplate Reduction via `_headless.py`

Each harness reduces to: import shared helpers, define capture callback,
call `patch_game_loop`, run script.

### Expected Line Count Reduction

| Harness | Before | After | Reduction |
|---------|--------|-------|-----------|
| harness.py | 93 | ~30 | -68% |
| frames_harness.py | 110 | ~35 | -68% |
| input_harness.py | 184 | ~90 | -51% |
| screen_harness.py | 108 | ~35 | -68% |
| state_harness.py | 169 | ~75 | -56% |
| layout_harness.py | 312 | ~200 | -36% |
| tilemap_harness.py | 132 | ~45 | -66% |
| bank_harness.py | 85 | ~30 | -65% |
| sprite_harness.py | 102 | ~40 | -61% |
| audio_harness.py | 80 | ~30 | -63% |

### layout_harness.py Decomposition

Split `_analyze_and_quit` (270+ lines) into testable functions:

```python
def read_pixels(w, h) -> list[list[int]]: ...
def find_bg_color(pixels) -> int: ...
def content_bbox(pixels, bg) -> dict | None: ...
def calc_balance(pixels, bg) -> dict: ...
def calc_margins(bbox, w, h) -> dict: ...
def detect_text(pixels, bg) -> list[dict]: ...
def merge_text_spans(spans) -> list[dict]: ...
def dedup_text_by_y(spans) -> list[dict]: ...
def analyze_text_alignment(text_lines, screen_w) -> list[dict]: ...
```

## Phase 5: Graphics & Design Enhancement

### 5a. inspect_sprite Improvements

- **Outline detection**: check color-0 outline completeness, warn on gaps
- **Color count validation**: 3-4 for 8x8, 5-6 for 16x16; warn on excess
- **Pillow shading detection**: dark edges + bright center pattern
- **Material hints**: suggest material names from color combinations
- **Empty space detection**: report all-zero regions for placement guidance

### 5b. inspect_layout Improvements

- **Custom font support**: auto-estimate font height from pixel continuity
- **UI element detection**: detect rectangular frames (buttons, panels)
- **Draw order warnings**: detect UI overlapping game area
- **Grid alignment check**: verify 8px/16px grid alignment

### 5c. inspect_palette Improvements

- **Color harmony analysis**: evaluate 3-layer hierarchy conformance
  (background / environment / interactive)
- **Color role estimation**: auto-classify bg, environment, player, enemy
- **WCAG-style contrast**: relative luminance calculation instead of
  simple brightness ratio
- **Unused color suggestions**: recommend palette additions

### 5d. New Tool: inspect_animation

Check sprite sheet animation frame consistency. Reuses `sprite_harness.py`
(which already patches game loop to no-ops) by reading multiple adjacent
regions in a single invocation.

```python
@mcp.tool()
async def inspect_animation(
    script_path: str,
    image: int = 0,
    x: int = 0, y: int = 0,
    w: int = 8, h: int = 8,
    frame_count: int = 2,
) -> str:
```

- Frame-to-frame palette consistency
- Silhouette size consistency
- Pixel change rate (smoothness)

### 5e. validate_script Expansion

Add anti-patterns:
- `for e in list:` + `list.remove()` mutation during iteration
- `pyxel.run()` called outside `__init__`
- Color literal > 15 without extended palette setup
- `blt()` without `colkey` argument

Note: "state mutation in draw()" and "btn() for one-shot actions" were
considered but excluded — both are highly context-dependent and would
produce excessive false positives. May revisit with AST-level analysis.

### 5f. Unified Output Format

All tools adopt fact-then-suggestion structure:

```
=== Analysis ===
(objective data)

=== Suggestions ===
- Fix: specific actionable fix
- Tip: improvement suggestion
```

## Phase 6: Testing

### Test Structure

```
tests/
  conftest.py              # Shared fixtures
  test_audio.py            # _audio.py unit tests
  test_palette.py          # _palette.py unit tests
  test_errors.py           # _errors.py unit tests
  test_validate.py         # _validate.py unit tests
  test_format.py           # _format.py unit tests
  test_subprocess.py       # _subprocess.py unit tests
  test_headless.py         # _headless.py unit tests
  test_layout_analysis.py  # layout_harness split function tests
  test_tools.py            # MCP tool integration tests
```

### Unit Tests (no Pyxel dependency)

- **test_audio.py**: sine wave frequency accuracy, note name conversion,
  key detection with known MIDI sequences, interval classification
- **test_palette.py**: contrast (white/black=max, same=1.0), names
- **test_errors.py**: pattern matching, stdout JSON extraction
- **test_validate.py**: each anti-pattern detection/non-detection
- **test_format.py**: sample JSON input → expected output strings

### Integration Tests (require Pyxel)

- **test_tools.py**: create minimal Pyxel scripts in temp files, invoke
  actual MCP tools, verify outputs

### Dependencies

```toml
[project.optional-dependencies]
test = ["pytest", "pytest-asyncio"]
```

## Out of Scope

- Sprite recipe templates (would become one-pattern)
- External pixel art site references (palette mismatch, runtime dependency)
- Sprite import from CC0 assets (previously tested and removed)

### 5f Note: instructions.md Update

The unified output format (`=== Analysis === / === Suggestions ===`)
requires updating the "Reading Tool Output" section in instructions.md
to match the new format. This is done as part of Phase 5f.

## Migration Notes

- Breaking changes to tool interfaces are acceptable
- numpy becomes a direct dependency in pyproject.toml
- _INSTRUCTIONS moves to instructions.md (loaded at startup)
- Harness CLI argument formats may change (internal only)
- All existing MCP tool names are preserved
- instructions.md must be included in package data (pyproject.toml update)
